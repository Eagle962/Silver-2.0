import datetime
import random
from utils.database import get_db_connection, execute_query, table_exists, column_exists
from models.currency import Currency

class Stock:
    """股票系統模型"""
    
    def __init__(self, bot):
        self.bot = bot
        self.db_name = "stock"
        self.price_change_limit = 0.1  # 每日漲跌停限制 10%
        
    async def setup_database(self):
        """初始化資料庫表格"""
        conn = await get_db_connection(self.db_name)
        cursor = await conn.cursor()
        
        # 股票表格
        await cursor.execute('''
        CREATE TABLE IF NOT EXISTS stocks (
            stock_id INTEGER PRIMARY KEY AUTOINCREMENT,
            stock_code TEXT UNIQUE,
            stock_name TEXT,
            issuer_id INTEGER,
            total_shares INTEGER,
            available_shares INTEGER,
            price REAL,
            initial_price REAL,
            last_price REAL,
            last_update TIMESTAMP,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 股權表格
        await cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock_holdings (
            holding_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            stock_id INTEGER,
            shares INTEGER,
            UNIQUE(user_id, stock_id),
            FOREIGN KEY (stock_id) REFERENCES stocks(stock_id)
        )
        ''')
        
        # 交易歷史表格
        await cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock_transactions (
            transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            stock_id INTEGER,
            seller_id INTEGER,
            buyer_id INTEGER,
            shares INTEGER,
            price_per_share REAL,
            total_amount REAL,
            transaction_type TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (stock_id) REFERENCES stocks(stock_id)
        )
        ''')
        
        # 股息歷史表格
        await cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock_dividends (
            dividend_id INTEGER PRIMARY KEY AUTOINCREMENT,
            stock_id INTEGER,
            amount_per_share REAL,
            issued_by INTEGER,
            issued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (stock_id) REFERENCES stocks(stock_id)
        )
        ''')
        
        # 每日價格記錄表格
        await cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock_price_history (
            record_id INTEGER PRIMARY KEY AUTOINCREMENT,
            stock_id INTEGER,
            price REAL,
            date DATE,
            UNIQUE(stock_id, date),
            FOREIGN KEY (stock_id) REFERENCES stocks(stock_id)
        )
        ''')
        
        # 委託單表格
        await cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock_orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            stock_id INTEGER,
            order_type TEXT,  -- 'buy' 或 'sell'
            shares INTEGER,
            price REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'active',  -- 'active', 'completed', 'canceled'
            FOREIGN KEY (stock_id) REFERENCES stocks(stock_id)
        )
        ''')
        
        await conn.commit()
    async def update_stock_price_directly(self, stock_id: int, new_price: float):
        """直接更新股票價格（用於定時波動）"""
        # 確保資料庫已設置
        await self.setup_database()
        
        # 獲取當前價格
        query = 'SELECT price FROM stocks WHERE stock_id = ?'
        result = await execute_query(self.db_name, query, (stock_id,), 'one')
        
        if not result:
            return
        
        current_price = result[0]
        
        # 更新價格
        query = '''
        UPDATE stocks 
        SET last_price = price, price = ?, last_update = CURRENT_TIMESTAMP
        WHERE stock_id = ?
        '''
        
        await execute_query(self.db_name, query, (new_price, stock_id))
        
        # 記錄每日價格
        today = datetime.date.today()
        
        query = '''
        INSERT INTO stock_price_history (stock_id, price, date)
        VALUES (?, ?, ?)
        ON CONFLICT(stock_id, date) 
        DO UPDATE SET price = ?
        '''
        
        await execute_query(self.db_name, query, (stock_id, new_price, today, new_price))
    
    async def issue_stock(self, user_id: int, stock_code: str, stock_name: str, initial_price: float, total_shares: int, description: str):
        """發行股票"""
        # 確保資料庫已設置
        await self.setup_database()
        
        # 檢查代碼是否已存在
        query = 'SELECT stock_id FROM stocks WHERE stock_code = ?'
        result = await execute_query(self.db_name, query, (stock_code,), 'one')
        
        if result:
            return False, "股票代碼已存在！"
        
        # 計算發行成本
        issue_cost = initial_price * total_shares * 0.05  # 發行費用為股票總價值的5%
        
        # 檢查用戶餘額
        currency = Currency(self.bot)
        balance = await currency.get_balance(user_id)
        
        if balance < issue_cost:
            return False, f"餘額不足！發行需要 {issue_cost:,.2f} Silva幣"
        
        # 扣除發行費用
        await currency.update_balance(user_id, -issue_cost, f"發行 {stock_code} 股票")
        
        # 添加股票到資料庫
        now = datetime.datetime.now()
        query = '''
        INSERT INTO stocks 
            (stock_code, stock_name, issuer_id, total_shares, available_shares, price, initial_price, last_price, last_update, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        
        await execute_query(
            self.db_name,
            query,
            (stock_code, stock_name, user_id, total_shares, 0, initial_price, initial_price, initial_price, now, description)
        )
        
        # 獲取新增的股票ID
        query = 'SELECT stock_id FROM stocks WHERE stock_code = ?'
        result = await execute_query(self.db_name, query, (stock_code,), 'one')
        stock_id = result[0]
        
        # 為發行人分配全部股份
        query = '''
        INSERT INTO stock_holdings (user_id, stock_id, shares)
        VALUES (?, ?, ?)
        '''
        
        await execute_query(self.db_name, query, (user_id, stock_id, total_shares))
        
        # 記錄股價歷史
        today = datetime.date.today()
        query = '''
        INSERT INTO stock_price_history (stock_id, price, date)
        VALUES (?, ?, ?)
        '''
        
        await execute_query(self.db_name, query, (stock_id, initial_price, today))
        
        return True, f"成功發行 {stock_name}({stock_code}) 股票，總股數: {total_shares}，價格: {initial_price} Silva幣"
    
    async def get_stock_info(self, stock_code: str):
        """獲取股票信息"""
        # 確保資料庫已設置
        await self.setup_database()
        
        query = '''
        SELECT 
            stock_id, stock_name, issuer_id, total_shares, available_shares, 
            price, initial_price, description, created_at
        FROM stocks 
        WHERE stock_code = ?
        '''
        
        result = await execute_query(self.db_name, query, (stock_code,), 'one')
        
        if not result:
            return None
        
        return {
            'stock_id': result[0],
            'stock_name': result[1],
            'issuer_id': result[2],
            'total_shares': result[3],
            'available_shares': result[4],
            'price': result[5],
            'initial_price': result[6],
            'description': result[7],
            'created_at': result[8]
        }
    
    async def get_all_stocks(self, limit=100):
        """獲取所有股票列表"""
        # 確保資料庫已設置
        await self.setup_database()
        
        query = '''
        SELECT 
            stock_id, stock_code, stock_name, price, total_shares, issuer_id
        FROM stocks
        ORDER BY stock_code
        LIMIT ?
        '''
        
        result = await execute_query(self.db_name, query, (limit,), 'all')
        return result
    
    async def get_user_stocks(self, user_id: int):
        """獲取用戶持有的股票"""
        # 確保資料庫已設置
        await self.setup_database()
        
        query = '''
        SELECT 
            s.stock_id, s.stock_code, s.stock_name, h.shares, s.price
        FROM stock_holdings h
        JOIN stocks s ON h.stock_id = s.stock_id
        WHERE h.user_id = ? AND h.shares > 0
        ORDER BY s.stock_code
        '''
        
        result = await execute_query(self.db_name, query, (user_id,), 'all')
        return result
    
    async def place_order(self, user_id: int, stock_code: str, order_type: str, shares: int, price: float):
        """下訂單購買或出售股票"""
        # 確保資料庫已設置
        await self.setup_database()
        
        # 獲取股票信息
        stock_info = await self.get_stock_info(stock_code)
        if not stock_info:
            return False, "找不到該股票！"
        
        stock_id = stock_info['stock_id']
        current_price = stock_info['price']
        
        # 檢查價格是否在漲跌停範圍內
        price_limit_low = current_price * (1 - self.price_change_limit)
        price_limit_high = current_price * (1 + self.price_change_limit)
        
        if price < price_limit_low or price > price_limit_high:
            return False, f"委託價格超出漲跌停範圍！允許範圍: {price_limit_low:.2f} ~ {price_limit_high:.2f}"
        
        if order_type == "buy":
            # 購買股票
            total_cost = price * shares
            
            # 檢查用戶餘額
            currency = Currency(self.bot)
            balance = await currency.get_balance(user_id)
            
            if balance < total_cost:
                return False, f"餘額不足！需要 {total_cost:,.2f} Silva幣"
            
            # 先扣除資金
            await currency.update_balance(user_id, -total_cost, f"購買 {stock_code} 股票委託下單")
            
        elif order_type == "sell":
            # 出售股票
            
            # 檢查用戶是否持有足夠的股份
            query = 'SELECT shares FROM stock_holdings WHERE user_id = ? AND stock_id = ?'
            result = await execute_query(self.db_name, query, (user_id, stock_id), 'one')
            
            if not result or result[0] < shares:
                return False, "持有股份不足！"
        
        # 添加訂單到資料庫
        query = '''
        INSERT INTO stock_orders 
            (user_id, stock_id, order_type, shares, price, created_at, status)
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, 'active')
        '''
        
        await execute_query(self.db_name, query, (user_id, stock_id, order_type, shares, price))
        
        # 嘗試撮合訂單
        matched = await self.match_orders(stock_id)
        
        if matched:
            return True, f"委託單已提交並成功撮合交易！"
        else:
            return True, f"委託單已提交，正在等待撮合！"
    
    async def match_orders(self, stock_id: int):
        """撮合買賣訂單"""
        # 獲取活躍的買賣訂單
        query_buy = '''
        SELECT order_id, user_id, shares, price 
        FROM stock_orders 
        WHERE stock_id = ? AND order_type = 'buy' AND status = 'active'
        ORDER BY price DESC, created_at ASC
        '''
        
        query_sell = '''
        SELECT order_id, user_id, shares, price 
        FROM stock_orders 
        WHERE stock_id = ? AND order_type = 'sell' AND status = 'active'
        ORDER BY price ASC, created_at ASC
        '''
        
        buy_orders = await execute_query(self.db_name, query_buy, (stock_id,), 'all')
        sell_orders = await execute_query(self.db_name, query_sell, (stock_id,), 'all')
        
        if not buy_orders or not sell_orders:
            return False
        
        matched = False
        
        # 撮合訂單
        for buy in buy_orders:
            buy_id, buyer_id, buy_shares, buy_price = buy
            
            for sell in sell_orders:
                sell_id, seller_id, sell_shares, sell_price = sell
                
                # 如果買入價格 >= 賣出價格，可以撮合
                if buy_price >= sell_price:
                    # 確定交易數量
                    trade_shares = min(buy_shares, sell_shares)
                    
                    # 確定交易價格（取買賣價格的平均值）
                    trade_price = (buy_price + sell_price) / 2
                    
                    # 執行交易
                    await self.execute_trade(stock_id, buyer_id, seller_id, trade_shares, trade_price)
                    
                    # 更新訂單狀態
                    await self.update_order_after_trade(buy_id, sell_id, trade_shares)
                    
                    matched = True
                    
                    # 如果賣單已全部撮合，跳出內循環
                    if sell_shares <= buy_shares:
                        break
            
            # 如果該買單已經被全部撮合，繼續下一個買單
            query = 'SELECT status FROM stock_orders WHERE order_id = ?'
            result = await execute_query(self.db_name, query, (buy_id,), 'one')
            
            if result and result[0] == 'completed':
                continue
        
        # 更新股票最新價格
        if matched:
            await self.update_stock_price(stock_id)
        
        return matched
    
    async def execute_trade(self, stock_id: int, buyer_id: int, seller_id: int, shares: int, price: float):
        """執行交易"""
        total_amount = shares * price
        
        # 獲取股票資訊
        query = 'SELECT stock_code FROM stocks WHERE stock_id = ?'
        result = await execute_query(self.db_name, query, (stock_id,), 'one')
        stock_code = result[0] if result else "未知股票"
        
        # 買家已經在下單時扣除了資金，現在返回多扣的部分
        currency = Currency(self.bot)
        refund = (price - price) * shares  # 如果買入價高於實際交易價，返回差額
        
        if refund > 0:
            await currency.update_balance(buyer_id, refund, f"股票 {stock_code} 交易退款")
        
        # 賣家獲得資金
        await currency.update_balance(seller_id, total_amount, f"出售 {stock_code} 股票")
        
        # 更新股權
        await self.update_holdings(buyer_id, stock_id, shares)
        await self.update_holdings(seller_id, stock_id, -shares)
        
        # 記錄交易歷史
        query = '''
        INSERT INTO stock_transactions 
            (stock_id, seller_id, buyer_id, shares, price_per_share, total_amount, transaction_type)
        VALUES (?, ?, ?, ?, ?, ?, 'market')
        '''
        
        await execute_query(
            self.db_name,
            query,
            (stock_id, seller_id, buyer_id, shares, price, total_amount)
        )
    
    async def update_order_after_trade(self, buy_order_id: int, sell_order_id: int, traded_shares: int):
        """交易後更新訂單狀態"""
        # 更新買單
        query = 'SELECT shares FROM stock_orders WHERE order_id = ?'
        result = await execute_query(self.db_name, query, (buy_order_id,), 'one')
        
        if result:
            remaining_shares = result[0] - traded_shares
            
            if remaining_shares <= 0:
                query = 'UPDATE stock_orders SET status = "completed", shares = 0 WHERE order_id = ?'
                await execute_query(self.db_name, query, (buy_order_id,))
            else:
                query = 'UPDATE stock_orders SET shares = ? WHERE order_id = ?'
                await execute_query(self.db_name, query, (remaining_shares, buy_order_id))
        
        # 更新賣單
        query = 'SELECT shares FROM stock_orders WHERE order_id = ?'
        result = await execute_query(self.db_name, query, (sell_order_id,), 'one')
        
        if result:
            remaining_shares = result[0] - traded_shares
            
            if remaining_shares <= 0:
                query = 'UPDATE stock_orders SET status = "completed", shares = 0 WHERE order_id = ?'
                await execute_query(self.db_name, query, (sell_order_id,))
            else:
                query = 'UPDATE stock_orders SET shares = ? WHERE order_id = ?'
                await execute_query(self.db_name, query, (remaining_shares, sell_order_id))
    
    async def update_holdings(self, user_id: int, stock_id: int, shares_change: int):
        """更新用戶持股"""
        query = 'SELECT holding_id, shares FROM stock_holdings WHERE user_id = ? AND stock_id = ?'
        result = await execute_query(self.db_name, query, (user_id, stock_id), 'one')
        
        if result:
            holding_id, current_shares = result
            new_shares = current_shares + shares_change
            
            if new_shares > 0:
                query = 'UPDATE stock_holdings SET shares = ? WHERE holding_id = ?'
                await execute_query(self.db_name, query, (new_shares, holding_id))
            else:
                query = 'DELETE FROM stock_holdings WHERE holding_id = ?'
                await execute_query(self.db_name, query, (holding_id,))
        elif shares_change > 0:
            query = 'INSERT INTO stock_holdings (user_id, stock_id, shares) VALUES (?, ?, ?)'
            await execute_query(self.db_name, query, (user_id, stock_id, shares_change))
    
    async def update_stock_price(self, stock_id: int):
        """更新股票價格"""
        # 獲取最近的交易價格
        query = '''
        SELECT price_per_share 
        FROM stock_transactions 
        WHERE stock_id = ? 
        ORDER BY created_at DESC 
        LIMIT 1
        '''
        
        result = await execute_query(self.db_name, query, (stock_id,), 'one')
        
        if not result:
            return
        
        last_trade_price = result[0]
        
        # 獲取當前價格
        query = 'SELECT price, last_price FROM stocks WHERE stock_id = ?'
        result = await execute_query(self.db_name, query, (stock_id,), 'one')
        
        if not result:
            return
        
        current_price, last_price = result
        
        # 更新價格
        query = '''
        UPDATE stocks 
        SET last_price = price, price = ?, last_update = CURRENT_TIMESTAMP
        WHERE stock_id = ?
        '''
        
        await execute_query(self.db_name, query, (last_trade_price, stock_id))
        
        # 記錄每日價格
        today = datetime.date.today()
        
        query = '''
        INSERT INTO stock_price_history (stock_id, price, date)
        VALUES (?, ?, ?)
        ON CONFLICT(stock_id, date) 
        DO UPDATE SET price = ?
        '''
        
        await execute_query(self.db_name, query, (stock_id, last_trade_price, today, last_trade_price))
    
    async def get_user_orders(self, user_id: int, active_only=False):
        """獲取用戶的委託單"""
        # 確保資料庫已設置
        await self.setup_database()
        
        query = '''
        SELECT 
            o.order_id, s.stock_code, s.stock_name, o.order_type, 
            o.shares, o.price, o.status, o.created_at
        FROM stock_orders o
        JOIN stocks s ON o.stock_id = s.stock_id
        WHERE o.user_id = ?
        '''
        
        if active_only:
            query += " AND o.status = 'active'"
            
        query += " ORDER BY o.created_at DESC"
        
        result = await execute_query(self.db_name, query, (user_id,), 'all')
        return result
    
    async def cancel_order(self, user_id: int, order_id: int):
        """取消委託單"""
        # 確保資料庫已設置
        await self.setup_database()
        
        # 檢查訂單是否存在且屬於該用戶
        query = '''
        SELECT 
            o.order_type, o.shares, o.price, o.status, s.stock_id, s.stock_code
        FROM stock_orders o
        JOIN stocks s ON o.stock_id = s.stock_id
        WHERE o.order_id = ? AND o.user_id = ?
        '''
        
        result = await execute_query(self.db_name, query, (order_id, user_id), 'one')
        
        if not result:
            return False, "找不到該委託單或您沒有權限取消！"
        
        order_type, shares, price, status, stock_id, stock_code = result
        
        if status != 'active':
            return False, "只能取消活躍中的委託單！"
        
        # 更新訂單狀態
        query = 'UPDATE stock_orders SET status = "canceled" WHERE order_id = ?'
        await execute_query(self.db_name, query, (order_id,))
        
        # 如果是購買訂單，退還資金
        if order_type == 'buy':
            refund_amount = shares * price
            currency = Currency(self.bot)
            await currency.update_balance(user_id, refund_amount, f"取消購買 {stock_code} 股票委託單")
        
        return True, f"成功取消委託單！"
    
    async def pay_dividend(self, user_id: int, stock_code: str, amount_per_share: float):
        """發放股息"""
        # 確保資料庫已設置
        await self.setup_database()
        
        # 獲取股票信息
        stock_info = await self.get_stock_info(stock_code)
        if not stock_info:
            return False, "找不到該股票！"
        
        stock_id = stock_info['stock_id']
        
        # 檢查是否為發行人
        if stock_info['issuer_id'] != user_id:
            return False, "只有股票發行人可以宣布派發股息！"
        
        # 計算總股息
        query = 'SELECT SUM(shares) FROM stock_holdings WHERE stock_id = ?'
        result = await execute_query(self.db_name, query, (stock_id,), 'one')
        
        if not result or not result[0]:
            return False, "沒有股東持有該股票！"
        
        total_shares = result[0]
        total_dividend = total_shares * amount_per_share
        
        # 檢查發行人餘額
        currency = Currency(self.bot)
        balance = await currency.get_balance(user_id)
        
        if balance < total_dividend:
            return False, f"餘額不足！需要 {total_dividend:,.2f} Silva幣來派發股息"
        
        # 扣除發行人資金
        await currency.update_balance(user_id, -total_dividend, f"為 {stock_code} 股票派發股息")
        
        # 記錄股息發放
        query = '''
        INSERT INTO stock_dividends (stock_id, amount_per_share, issued_by)
        VALUES (?, ?, ?)
        '''
        
        await execute_query(self.db_name, query, (stock_id, amount_per_share, user_id))
        
        # 獲取所有股東
        query = 'SELECT user_id, shares FROM stock_holdings WHERE stock_id = ?'
        shareholders = await execute_query(self.db_name, query, (stock_id,), 'all')
        
        # 向股東分發股息
        for shareholder_id, shares in shareholders:
            dividend_amount = shares * amount_per_share
            await currency.update_balance(shareholder_id, dividend_amount, f"從 {stock_code} 股票收到的股息")
        
        return True, f"成功為 {stock_code} 派發每股 {amount_per_share} Silva幣的股息，總計 {total_dividend:,.2f} Silva幣"
    
    async def get_price_history(self, stock_code: str, days=30):
        """獲取股票價格歷史"""
        # 確保資料庫已設置
        await self.setup_database()
        
        # 獲取股票ID
        query = 'SELECT stock_id FROM stocks WHERE stock_code = ?'
        result = await execute_query(self.db_name, query, (stock_code,), 'one')
        
        if not result:
            return None
        
        stock_id = result[0]
        
        # 獲取價格歷史
        query = '''
        SELECT date, price
        FROM stock_price_history
        WHERE stock_id = ?
        ORDER BY date DESC
        LIMIT ?
        '''
        
        result = await execute_query(self.db_name, query, (stock_id, days), 'all')
        return result
    
    async def get_stock_market_value(self, user_id: int):
        """獲取用戶股票市值"""
        # 確保資料庫已設置
        await self.setup_database()
        
        query = '''
        SELECT 
            SUM(h.shares * s.price) as market_value
        FROM stock_holdings h
        JOIN stocks s ON h.stock_id = s.stock_id
        WHERE h.user_id = ?
        '''
        
        result = await execute_query(self.db_name, query, (user_id,), 'one')
        
        if result and result[0]:
            return result[0]
        return 0
    
    async def get_top_stocks(self, limit=5):
        """獲取漲幅最高的股票"""
        # 確保資料庫已設置
        await self.setup_database()
        
        query = '''
        SELECT 
            stock_code, stock_name, price, 
            ROUND(((price / last_price) - 1) * 100, 2) as change_percent
        FROM stocks
        WHERE last_price > 0
        ORDER BY change_percent DESC
        LIMIT ?
        '''
        
        result = await execute_query(self.db_name, query, (limit,), 'all')
        return result

    async def get_stock_shareholders(self, stock_code: str, limit=10):
        """獲取股票的股東列表"""
        # 確保資料庫已設置
        await self.setup_database()
        
        # 獲取股票ID
        query = 'SELECT stock_id FROM stocks WHERE stock_code = ?'
        result = await execute_query(self.db_name, query, (stock_code,), 'one')
        
        if not result:
            return None
        
        stock_id = result[0]
        
        # 獲取股東列表
        query = '''
        SELECT 
            h.user_id, h.shares, 
            ROUND((h.shares * 100.0) / (SELECT SUM(shares) FROM stock_holdings WHERE stock_id = ?), 2) as percentage
        FROM stock_holdings h
        WHERE h.stock_id = ?
        ORDER BY h.shares DESC
        LIMIT ?
        '''
        
        result = await execute_query(self.db_name, query, (stock_id, stock_id, limit), 'all')
        return result