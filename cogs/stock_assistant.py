import discord
from discord.ext import commands, tasks
from discord import app_commands
import random
import asyncio
import datetime
from models.currency import Currency
from models.stocks import Stock
from utils.database import get_db_connection, execute_query, table_exists

class TradingAssistantSystem:
    """交易助理系統模型"""
    
    def __init__(self, bot):
        self.bot = bot
        self.db_name = "trading_assistants"
        
    async def setup_database(self):
        """初始化資料庫表格"""
        conn = await get_db_connection(self.db_name)
        cursor = await conn.cursor()
        
        # 交易助理表格
        await cursor.execute('''
        CREATE TABLE IF NOT EXISTS assistants (
            assistant_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            assistant_name TEXT,
            rarity TEXT,
            obtained_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            active INTEGER DEFAULT 0
        )
        ''')
        
        # 助理設定表格
        await cursor.execute('''
        CREATE TABLE IF NOT EXISTS assistant_settings (
            setting_id INTEGER PRIMARY KEY AUTOINCREMENT,
            assistant_id INTEGER,
            setting_key TEXT,
            setting_value TEXT,
            FOREIGN KEY (assistant_id) REFERENCES assistants(assistant_id)
        )
        ''')
        
        # 助理監控的股票表格
        await cursor.execute('''
        CREATE TABLE IF NOT EXISTS assistant_stocks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assistant_id INTEGER,
            stock_code TEXT,
            FOREIGN KEY (assistant_id) REFERENCES assistants(assistant_id)
        )
        ''')
        
        # 助理交易記錄表格
        await cursor.execute('''
        CREATE TABLE IF NOT EXISTS assistant_trades (
            trade_id INTEGER PRIMARY KEY AUTOINCREMENT,
            assistant_id INTEGER,
            stock_code TEXT,
            trade_type TEXT,
            shares INTEGER,
            price REAL,
            total_amount REAL,
            profit_loss REAL,
            trade_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (assistant_id) REFERENCES assistants(assistant_id)
        )
        ''')
        
        await conn.commit()
    
    async def draw_assistant(self, user_id: int, username: str) -> dict:
        """抽取一個交易助理"""
        await self.setup_database()
        
        # 先扣除Silva幣
        currency = Currency(self.bot)
        balance = await currency.get_balance(user_id)
        
        if balance < 2000:
            return {'success': False, 'message': '餘額不足，抽獎需要2000 Silva幣！'}
        
        await currency.update_balance(user_id, -2000, f"{username} 抽取交易助理")
        
        # 抽獎邏輯
        rarity_roll = random.random() * 100
        
        if rarity_roll < 5:  # 5%
            rarity = "SSR"
            assistant_prefix = "智能全能"
        elif rarity_roll < 15:  # 10%
            rarity = "SR"
            assistant_prefix = "精英戰術"
        elif rarity_roll < 40:  # 25%
            rarity = "R"
            assistant_prefix = "專業分析"
        else:  # 60%
            rarity = "N"
            assistant_prefix = "初級顧問"
        
        # 生成助理名稱
        adjectives = ["鋒銳的", "睿智的", "敏銳的", "謹慎的", "果斷的", "精明的", "洞察的", "冷靜的", "勤勉的", "先知的"]
        nouns = ["掠鷹", "獵豹", "戰略家", "預言家", "觀察者", "掌控者", "操盤手", "判客", "贏家", "傳奇"]
        
        assistant_name = f"{assistant_prefix} {random.choice(adjectives)}{random.choice(nouns)}"
        
        # 儲存到資料庫
        query = '''
        INSERT INTO assistants (user_id, assistant_name, rarity, obtained_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        '''
        
        result = await execute_query(self.db_name, query, (user_id, assistant_name, rarity))
        assistant_id = result
        
        # 返回結果
        return {
            'success': True,
            'assistant_id': assistant_id,
            'assistant_name': assistant_name,
            'rarity': rarity
        }
    
    async def get_user_assistants(self, user_id: int) -> list:
        """獲取用戶所有的交易助理"""
        await self.setup_database()
        
        query = '''
        SELECT assistant_id, assistant_name, rarity, obtained_at, active
        FROM assistants
        WHERE user_id = ?
        ORDER BY rarity DESC, obtained_at DESC
        '''
        
        result = await execute_query(self.db_name, query, (user_id,), 'all')
        return result
    
    async def get_assistant_details(self, assistant_id: int) -> dict:
        """獲取助理的詳細資訊"""
        await self.setup_database()
        
        # 獲取基本資訊
        query = '''
        SELECT assistant_id, user_id, assistant_name, rarity, obtained_at, active
        FROM assistants
        WHERE assistant_id = ?
        '''
        
        assistant = await execute_query(self.db_name, query, (assistant_id,), 'one')
        
        if not assistant:
            return None
            
        # 獲取設定
        query = '''
        SELECT setting_key, setting_value
        FROM assistant_settings
        WHERE assistant_id = ?
        '''
        
        settings_rows = await execute_query(self.db_name, query, (assistant_id,), 'all')
        settings = {row[0]: row[1] for row in settings_rows} if settings_rows else {}
        
        # 獲取監控的股票
        query = '''
        SELECT stock_code
        FROM assistant_stocks
        WHERE assistant_id = ?
        '''
        
        stocks_rows = await execute_query(self.db_name, query, (assistant_id,), 'all')
        stocks = [row[0] for row in stocks_rows] if stocks_rows else []
        
        # 獲取最近的交易記錄
        query = '''
        SELECT trade_type, stock_code, shares, price, total_amount, profit_loss, trade_at
        FROM assistant_trades
        WHERE assistant_id = ?
        ORDER BY trade_at DESC
        LIMIT 10
        '''
        
        trades = await execute_query(self.db_name, query, (assistant_id,), 'all')
        
        # 計算總收益
        query = '''
        SELECT SUM(profit_loss)
        FROM assistant_trades
        WHERE assistant_id = ?
        '''
        
        total_profit_result = await execute_query(self.db_name, query, (assistant_id,), 'one')
        total_profit = total_profit_result[0] if total_profit_result and total_profit_result[0] else 0
        
        # 組合結果
        return {
            'assistant_id': assistant[0],
            'user_id': assistant[1],
            'assistant_name': assistant[2],
            'rarity': assistant[3],
            'obtained_at': assistant[4],
            'active': assistant[5],
            'settings': settings,
            'stocks': stocks,
            'trades': trades,
            'total_profit': total_profit
        }
    
    async def toggle_assistant_active(self, assistant_id: int, user_id: int) -> bool:
        """開啟或關閉交易助理"""
        await self.setup_database()
        
        # 檢查助理是否屬於該用戶
        query = '''
        SELECT active
        FROM assistants
        WHERE assistant_id = ? AND user_id = ?
        '''
        
        result = await execute_query(self.db_name, query, (assistant_id, user_id), 'one')
        
        if not result:
            return False
            
        current_status = result[0]
        new_status = 0 if current_status else 1
        
        # 如果要激活，先停用其他助理
        if new_status == 1:
            query = '''
            UPDATE assistants
            SET active = 0
            WHERE user_id = ? AND active = 1
            '''
            
            await execute_query(self.db_name, query, (user_id,))
        
        # 更新狀態
        query = '''
        UPDATE assistants
        SET active = ?
        WHERE assistant_id = ?
        '''
        
        await execute_query(self.db_name, query, (new_status, assistant_id))
        
        return True
    
    async def update_assistant_settings(self, assistant_id: int, user_id: int, settings: dict) -> bool:
        """更新助理設定"""
        await self.setup_database()
        
        # 檢查助理是否屬於該用戶
        query = '''
        SELECT rarity
        FROM assistants
        WHERE assistant_id = ? AND user_id = ?
        '''
        
        result = await execute_query(self.db_name, query, (assistant_id, user_id), 'one')
        
        if not result:
            return False
            
        rarity = result[0]
        
        # 清除現有設定
        query = '''
        DELETE FROM assistant_settings
        WHERE assistant_id = ?
        '''
        
        await execute_query(self.db_name, query, (assistant_id,))
        
        # 插入新設定
        for key, value in settings.items():
            query = '''
            INSERT INTO assistant_settings (assistant_id, setting_key, setting_value)
            VALUES (?, ?, ?)
            '''
            
            await execute_query(self.db_name, query, (assistant_id, key, value))
        
        return True
    
    async def update_assistant_stocks(self, assistant_id: int, user_id: int, stocks: list) -> bool:
        """更新助理監控的股票"""
        await self.setup_database()
        
        # 檢查助理是否屬於該用戶
        query = '''
        SELECT rarity
        FROM assistants
        WHERE assistant_id = ? AND user_id = ?
        '''
        
        result = await execute_query(self.db_name, query, (assistant_id, user_id), 'one')
        
        if not result:
            return False
            
        rarity = result[0]
        
        # 檢查股票數量是否超過限制
        max_stocks = {
            'N': 1,
            'R': 3,
            'SR': 5,
            'SSR': 100  # 實際上不限制
        }
        
        if len(stocks) > max_stocks[rarity]:
            return False
        
        # 清除現有股票
        query = '''
        DELETE FROM assistant_stocks
        WHERE assistant_id = ?
        '''
        
        await execute_query(self.db_name, query, (assistant_id,))
        
        # 插入新股票
        for stock_code in stocks:
            query = '''
            INSERT INTO assistant_stocks (assistant_id, stock_code)
            VALUES (?, ?)
            '''
            
            await execute_query(self.db_name, query, (assistant_id, stock_code))
        
        return True
    
    async def record_trade(self, assistant_id: int, stock_code: str, trade_type: str, 
                           shares: int, price: float, total_amount: float, profit_loss: float = 0) -> bool:
        """記錄交易"""
        await self.setup_database()
        
        query = '''
        INSERT INTO assistant_trades 
            (assistant_id, stock_code, trade_type, shares, price, total_amount, profit_loss)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        '''
        
        await execute_query(
            self.db_name,
            query,
            (assistant_id, stock_code, trade_type, shares, price, total_amount, profit_loss)
        )
        
        return True

    async def execute_trading_strategy(self):
        """執行所有活躍助理的交易策略"""
        await self.setup_database()
        
        # 獲取所有活躍的助理
        query = '''
        SELECT assistant_id, user_id, assistant_name, rarity
        FROM assistants
        WHERE active = 1
        '''
        
        active_assistants = await execute_query(self.db_name, query, fetch_type='all')
        
        if not active_assistants:
            return
        
        stock_system = Stock(self.bot)
        currency = Currency(self.bot)
        
        for assistant_id, user_id, assistant_name, rarity in active_assistants:
            # 獲取助理設定
            query = '''
            SELECT setting_key, setting_value
            FROM assistant_settings
            WHERE assistant_id = ?
            '''
            
            settings_rows = await execute_query(self.db_name, query, (assistant_id,), 'all')
            settings = {row[0]: row[1] for row in settings_rows} if settings_rows else {}
            
            # 獲取監控的股票
            query = '''
            SELECT stock_code
            FROM assistant_stocks
            WHERE assistant_id = ?
            '''
            
            stocks_rows = await execute_query(self.db_name, query, (assistant_id,), 'all')
            monitored_stocks = [row[0] for row in stocks_rows] if stocks_rows else []
            
            # 針對每支股票進行交易分析
            for stock_code in monitored_stocks:
                # 獲取股票資訊
                stock_info = await stock_system.get_stock_info(stock_code)
                
                if not stock_info:
                    continue
                
                # 根據稀有度和設定執行不同的交易策略
                try:
                    if rarity == 'N':
                        await self._execute_n_strategy(assistant_id, user_id, stock_code, stock_info, settings)
                    elif rarity == 'R':
                        await self._execute_r_strategy(assistant_id, user_id, stock_code, stock_info, settings)
                    elif rarity == 'SR':
                        await self._execute_sr_strategy(assistant_id, user_id, stock_code, stock_info, settings)
                    elif rarity == 'SSR':
                        await self._execute_ssr_strategy(assistant_id, user_id, stock_code, stock_info, settings)
                except Exception as e:
                    print(f"執行交易策略時發生錯誤: {e}")
    
    async def _execute_n_strategy(self, assistant_id, user_id, stock_code, stock_info, settings):
        """執行N級助理的交易策略"""
        current_price = stock_info['price']
        
        # 獲取設定值或使用預設值
        buy_threshold = float(settings.get('buy_threshold', 0))
        sell_threshold = float(settings.get('sell_threshold', float('inf')))
        trade_percentage = float(settings.get('trade_percentage', 10)) / 100  # 預設交易10%資金
        
        # 檢查是否符合買入條件
        if buy_threshold > 0 and current_price <= buy_threshold:
            await self._execute_buy_trade(assistant_id, user_id, stock_code, current_price, trade_percentage)
        
        # 檢查是否符合賣出條件
        if sell_threshold < float('inf') and current_price >= sell_threshold:
            await self._execute_sell_trade(assistant_id, user_id, stock_code, current_price, trade_percentage)
    
    async def _execute_r_strategy(self, assistant_id, user_id, stock_code, stock_info, settings):
        """執行R級助理的交易策略"""
        current_price = stock_info['price']
        
        # 獲取設定值
        buy_threshold = float(settings.get('buy_threshold', 0))
        sell_threshold = float(settings.get('sell_threshold', float('inf')))
        stop_loss = float(settings.get('stop_loss', 0))
        ma_short = int(settings.get('ma_short', 5))
        ma_long = int(settings.get('ma_long', 20))
        trade_percentage = float(settings.get('trade_percentage', 15)) / 100  # 預設交易15%資金
        
        # 獲取價格歷史
        stock_system = Stock(self.bot)
        price_history = await stock_system.get_price_history(stock_code, 30)
        
        if not price_history or len(price_history) < max(ma_short, ma_long):
            return
        
        # 計算移動平均線
        prices = [price for _, price in price_history]
        prices.reverse()  # 確保從舊到新排序
        
        ma_short_value = sum(prices[-ma_short:]) / ma_short
        ma_long_value = sum(prices[-ma_long:]) / ma_long
        
        # 移動平均線交叉策略
        ma_crossover_buy = ma_short_value > ma_long_value and prices[-2] <= ma_long_value
        ma_crossover_sell = ma_short_value < ma_long_value and prices[-2] >= ma_long_value
        
        # 檢查是否符合買入條件
        if (buy_threshold > 0 and current_price <= buy_threshold) or ma_crossover_buy:
            # 市場下跌時加大交易量
            if ma_short_value < prices[-5]:
                trade_percentage *= 1.5
            
            await self._execute_buy_trade(assistant_id, user_id, stock_code, current_price, trade_percentage)
        
        # 檢查是否符合賣出條件
        if (sell_threshold < float('inf') and current_price >= sell_threshold) or ma_crossover_sell:
            # 市場上漲時減少交易量
            if ma_short_value > prices[-5]:
                trade_percentage *= 0.8
                
            await self._execute_sell_trade(assistant_id, user_id, stock_code, current_price, trade_percentage)
        
        # 檢查止損
        if stop_loss > 0:
            # 獲取用戶持股平均成本
            user_holdings = await stock_system.get_user_stocks(user_id)
            for stock_id, code, name, shares, avg_price in user_holdings:
                if code == stock_code and current_price <= avg_price * (1 - stop_loss / 100):
                    # 觸發止損，賣出所有持股
                    await self._execute_sell_trade(assistant_id, user_id, stock_code, current_price, 1.0)
    
    async def _execute_sr_strategy(self, assistant_id, user_id, stock_code, stock_info, settings):
        """執行SR級助理的交易策略"""
        current_price = stock_info['price']
        
        # 獲取設定值
        use_rsi = settings.get('use_rsi', 'true') == 'true'
        rsi_buy = float(settings.get('rsi_buy', 30))
        rsi_sell = float(settings.get('rsi_sell', 70))
        use_macd = settings.get('use_macd', 'true') == 'true'
        use_pattern = settings.get('use_pattern', 'true') == 'true'
        risk_reward = float(settings.get('risk_reward', 2))
        trade_percentage = float(settings.get('trade_percentage', 20)) / 100
        
        # 獲取價格歷史
        stock_system = Stock(self.bot)
        price_history = await stock_system.get_price_history(stock_code, 60)
        
        if not price_history or len(price_history) < 30:
            return
        
        # 計算技術指標
        prices = [price for _, price in price_history]
        prices.reverse()
        
        # 計算RSI (簡化版)
        if use_rsi and len(prices) >= 14:
            changes = [prices[i] - prices[i-1] for i in range(1, len(prices))]
            gains = [max(0, change) for change in changes]
            losses = [max(0, -change) for change in changes]
            
            avg_gain = sum(gains[-14:]) / 14
            avg_loss = sum(losses[-14:]) / 14
            
            if avg_loss == 0:
                rsi = 100
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
        else:
            rsi = 50
        
        # 計算MACD (簡化版)
        if use_macd and len(prices) >= 26:
            ema12 = sum(prices[-12:]) / 12
            ema26 = sum(prices[-26:]) / 26
            macd = ema12 - ema26
            signal = sum([prices[-(i+1)] - prices[-(i+2)] for i in range(9)]) / 9
            macd_histogram = macd - signal
        else:
            macd_histogram = 0
            
        # 識別形態 (簡化版)
        pattern_bullish = False
        pattern_bearish = False
        
        if use_pattern and len(prices) >= 5:
            # 簡單的價格反轉模式
            if prices[-3] < prices[-4] < prices[-5] and prices[-1] > prices[-2] > prices[-3]:
                pattern_bullish = True
            elif prices[-3] > prices[-4] > prices[-5] and prices[-1] < prices[-2] < prices[-3]:
                pattern_bearish = True
        
        # 交易決策
        buy_signals = 0
        sell_signals = 0
        
        # RSI信號
        if use_rsi:
            if rsi <= rsi_buy:
                buy_signals += 1
            elif rsi >= rsi_sell:
                sell_signals += 1
        
        # MACD信號
        if use_macd:
            if macd_histogram > 0:
                buy_signals += 1
            elif macd_histogram < 0:
                sell_signals += 1
        
        # 形態信號
        if use_pattern:
            if pattern_bullish:
                buy_signals += 1
            elif pattern_bearish:
                sell_signals += 1
        
        # 市場波動調整
        volatility = sum([abs(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, min(20, len(prices)))]) / min(19, len(prices)-1)
        if volatility > 0.02:  # 高波動
            trade_percentage *= 0.8  # 減少交易量
        
        # 執行交易
        total_signals = (use_rsi + use_macd + use_pattern)
        if total_signals > 0:
            # 需要過半指標給出信號
            if buy_signals > total_signals / 2:
                # 根據信號強度調整交易量
                signal_strength = buy_signals / total_signals
                adjusted_percentage = trade_percentage * signal_strength * (1 + risk_reward)
                
                await self._execute_buy_trade(assistant_id, user_id, stock_code, current_price, adjusted_percentage)
            
            if sell_signals > total_signals / 2:
                signal_strength = sell_signals / total_signals
                adjusted_percentage = trade_percentage * signal_strength
                
                await self._execute_sell_trade(assistant_id, user_id, stock_code, current_price, adjusted_percentage)
    
    async def _execute_ssr_strategy(self, assistant_id, user_id, stock_code, stock_info, settings):
        """執行SSR級助理的交易策略"""
        current_price = stock_info['price']
        
        # 獲取設定值 (SSR可以設定更多高級參數)
        strategy_type = settings.get('strategy_type', 'balanced')
        risk_level = float(settings.get('risk_level', 0.5))
        use_sentiment = settings.get('use_sentiment', 'true') == 'true'
        trade_percentage = float(settings.get('trade_percentage', 25)) / 100
        auto_balance = settings.get('auto_balance', 'true') == 'true'
        
        # 獲取價格歷史和市場數據
        stock_system = Stock(self.bot)
        price_history = await stock_system.get_price_history(stock_code, 90)
        
        if not price_history or len(price_history) < 30:
            return
        
        # 獲取用戶投資組合
        user_holdings = await stock_system.get_user_stocks(user_id)
        portfolio_value = sum([shares * price for _, _, _, shares, price in user_holdings])
        
        # 計算複雜的指標 (這裡簡化實現)
        prices = [price for _, price in price_history]
        prices.reverse()
        
        # 計算多重時間週期的移動平均線
        ma_short = sum(prices[-5:]) / 5
        ma_medium = sum(prices[-20:]) / 20
        ma_long = sum(prices[-50:]) / 50
        
        # 計算波動率
        volatility = sum([abs(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, min(20, len(prices)))]) / min(19, len(prices)-1)
        
        # 市場週期判斷
        if ma_short > ma_medium > ma_long:
            market_cycle = "uptrend"
        elif ma_short < ma_medium < ma_long:
            market_cycle = "downtrend"
        else:
            market_cycle = "sideways"
        
        # 異常檢測 (簡化版)
        recent_avg = sum(prices[-5:]) / 5
        monthly_avg = sum(prices[-30:]) / 30
        price_anomaly = abs(recent_avg - monthly_avg) / monthly_avg > 0.15
        
        # 情緒分析模擬 (實際系統需要更複雜的實現)
        if use_sentiment:
            # 簡單模擬市場情緒，實際系統需要從新聞或社交媒體分析
            sentiment_score = random.uniform(-1, 1)
        else:
            sentiment_score = 0
        
        # 幸運交易機制
        lucky_trade = random.random() < 0.05  # 5%機率
        if lucky_trade:
            luck_bonus = random.uniform(0.1, 0.5)  # 10-50%的額外收益
        else:
            luck_bonus = 0
        
        # 根據策略類型調整參數
        if strategy_type == 'aggressive':
            trade_percentage *= 1.5
            risk_level *= 1.3
        elif strategy_type == 'conservative':
            trade_percentage *= 0.7
            risk_level *= 0.7
        
        # 交易決策
        buy_score = 0
        sell_score = 0
        
        # 價格相對均線
        if current_price < ma_short < ma_medium:
            buy_score += 0.2
        elif current_price > ma_short > ma_medium:
            sell_score += 0.2
        
        # 市場週期
        if market_cycle == "uptrend":
            buy_score += 0.15
        elif market_cycle == "downtrend":
            sell_score += 0.15
        
        # 異常檢測
        if price_anomaly:
            if current_price < monthly_avg:
                buy_score += 0.3
            else:
                sell_score += 0.3
        
        # 情緒分析
        buy_score += sentiment_score * 0.2
        sell_score -= sentiment_score * 0.2
        
        # 波動率調整
        if volatility > 0.03:  # 高波動
            trade_percentage *= (1 - volatility * 5)  # 降低交易量
        
        # 投資組合平衡
        if auto_balance and portfolio_value > 0:
            current_holdings = 0
            for _, code, _, shares, price in user_holdings:
                if code == stock_code:
                    current_holdings = shares * price
                    break
            
            # 計算目標比例 (根據風險水平)
            target_percentage = 0.2 * risk_level  # 假設最高投入20%
            current_percentage = current_holdings / portfolio_value
            
            if current_percentage < target_percentage * 0.8:
                buy_score += 0.25
            elif current_percentage > target_percentage * 1.2:
                sell_score += 0.25
        
        # 執行交易
        if buy_score > 0.5 or (lucky_trade and random.random() < 0.7):
            # 幸運交易增加買入量
            final_percentage = trade_percentage * (1 + buy_score * risk_level) * (1 + luck_bonus)
            await self._execute_buy_trade(assistant_id, user_id, stock_code, current_price, final_percentage)
        
        if sell_score > 0.5 or (lucky_trade and random.random() >= 0.7):
            # 幸運交易增加賣出收益
            final_percentage = trade_percentage * (1 + sell_score * risk_level) * (1 + luck_bonus)
            await self._execute_sell_trade(assistant_id, user_id, stock_code, current_price, final_percentage)
    
    async def _execute_buy_trade(self, assistant_id, user_id, stock_code, price, percentage):
        """執行買入交易"""
        # 獲取用戶餘額
        currency = Currency(self.bot)
        balance = await currency.get_balance(user_id)
        
        if balance <= 0:
            return
        
        # 計算買入金額
        buy_amount = balance * percentage
        if buy_amount < price:  # 確保至少能買1股
            return
            
        # 計算買入股數
        shares = int(buy_amount / price)
        total_amount = shares * price
        
        if shares <= 0 or total_amount > balance:
            return
        
        # 執行買入
        stock_system = Stock(self.bot)
        success, message = await stock_system.place_order(
            user_id, 
            stock_code, 
            "buy", 
            shares, 
            price
        )
        
        if success:
            # 記錄交易
            await self.record_trade(
                assistant_id, 
                stock_code, 
                "buy", 
                shares, 
                price, 
                total_amount
            )
    
    async def _execute_sell_trade(self, assistant_id, user_id, stock_code, price, percentage):
        """執行賣出交易"""
        # 獲取用戶持股
        stock_system = Stock(self.bot)
        user_holdings = await stock_system.get_user_stocks(user_id)
        
        user_shares = 0
        avg_cost = 0
        
        for stock_id, code, name, shares, avg_price in user_holdings:
            if code == stock_code:
                user_shares = shares
                avg_cost = avg_price
                break
        
        if user_shares <= 0:
            return
        
        # 計算賣出股數
        sell_shares = max(1, int(user_shares * percentage))
        if sell_shares <= 0:
            return
            
        total_amount = sell_shares * price
        
        # 執行賣出
        success, message = await stock_system.place_order(
            user_id, 
            stock_code, 
            "sell", 
            sell_shares, 
            price
        )
        
        if success:
            # 計算盈虧
            profit_loss = (price - avg_cost) * sell_shares
            
            # 記錄交易
            await self.record_trade(
                assistant_id, 
                stock_code, 
                "sell", 
                sell_shares, 
                price, 
                total_amount,
                profit_loss
            )
        
class TradingAssistantCog(commands.Cog):
    """交易助理系統指令"""

    def __init__(self, bot):
        self.bot = bot
        self.assistant_system = TradingAssistantSystem(bot)
        self.trading_task = self.start_trading_task()
        
    def cog_unload(self):
        """Cog卸載時取消任務"""
        self.trading_task.cancel()
        
    def start_trading_task(self):
        """啟動交易任務"""
        return self.bot.loop.create_task(self.trading_loop())
        
    async def trading_loop(self):
        """交易循環任務"""
        await self.bot.wait_until_ready()
        
        while not self.bot.is_closed():
            try:
                # 執行交易策略
                await self.assistant_system.execute_trading_strategy()
                
                # 等待一段時間
                await asyncio.sleep(3600)  # 每小時執行一次
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"交易循環任務發生錯誤: {e}")
                await asyncio.sleep(300)  # 發生錯誤後等待5分鐘
    
    @app_commands.command(name="draw_assistant", description="抽取一位股票交易助理 (花費2000 Silva幣)")
    async def draw_assistant(self, interaction: discord.Interaction):
        """抽取一位股票交易助理"""
        result = await self.assistant_system.draw_assistant(interaction.user.id, interaction.user.name)
        
        if not result['success']:
            await interaction.response.send_message(result['message'], ephemeral=True)
            return
        
        # 創建抽獎結果訊息
        rarity = result['rarity']
        
        rarity_colors = {
            'N': discord.Color.light_grey(),
            'R': discord.Color.blue(),
            'SR': discord.Color.purple(),
            'SSR': discord.Color.gold()
        }
        
        rarity_emojis = {
            'N': '⚪',
            'R': '🔵',
            'SR': '🟣',
            'SSR': '🟡'
        }
        
        rarity_display = {
            'N': '普通',
            'R': '稀有',
            'SR': '超稀有',
            'SSR': '極稀有'
        }
        
        embed = discord.Embed(
            title=f"🎮 交易助理抽獎結果",
            description=f"恭喜獲得 {rarity_emojis[rarity]} **{rarity_display[rarity]}** 交易助理！",
            color=rarity_colors[rarity]
        )
        
        embed.add_field(name="助理名稱", value=result['assistant_name'], inline=False)
        
        abilities = {
            'N': "• 每日交易一次\n• 基本價格門檻策略\n• 可監控 1 支股票\n• 簡單的買賣策略",
            'R': "• 每日交易兩次\n• 移動平均線策略\n• 可監控 3 支股票\n• 支援止損設定",
            'SR': "• 每日交易四次\n• 多重技術指標分析\n• 可監控 5 支股票\n• 支援形態識別和風險管理",
            'SSR': "• 每小時交易檢查\n• AI增強交易系統\n• 無限制監控股票數\n• 投資組合自動平衡\n• 幸運交易機制"
        }
        
        embed.add_field(name="能力", value=abilities[rarity], inline=False)
        
        if rarity == 'SSR':
            embed.set_footer(text="恭喜抽到了最稀有的SSR級助理！")
        elif rarity == 'SR':
            embed.set_footer(text="很棒！SR級助理擁有強大的交易能力。")
        elif rarity == 'R':
            embed.set_footer(text="不錯！R級助理能夠使用更多交易策略。")
        else:
            embed.set_footer(text="N級助理能提供基本的交易幫助。")
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="my_assistants", description="查看你的交易助理")
    async def my_assistants(self, interaction: discord.Interaction):
        """查看你的交易助理"""
        assistants = await self.assistant_system.get_user_assistants(interaction.user.id)
        
        if not assistants:
            await interaction.response.send_message("你還沒有任何交易助理！使用 `/draw_assistant` 來抽取一位。", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🤖 你的交易助理",
            description=f"你擁有 {len(assistants)} 位交易助理",
            color=discord.Color.blue()
        )
        
        rarity_emojis = {
            'N': '⚪',
            'R': '🔵',
            'SR': '🟣',
            'SSR': '🟡'
        }
        
        for assistant_id, name, rarity, obtained_at, active in assistants:
            status = "✅ 活躍中" if active else "⏸️ 未啟用"
            
            embed.add_field(
                name=f"{rarity_emojis[rarity]} {name} ({rarity})",
                value=f"ID: {assistant_id}\n狀態: {status}\n獲得時間: {obtained_at}",
                inline=True
            )
        
        # 創建視圖
        view = discord.ui.View(timeout=180)
        
        for assistant_id, name, rarity, obtained_at, active in assistants:
            button_label = f"{'停用' if active else '啟用'} {name}"
            button_style = discord.ButtonStyle.red if active else discord.ButtonStyle.green
            
            button = discord.ui.Button(label=button_label, style=button_style, custom_id=f"toggle_{assistant_id}")
            
            async def create_toggle_callback(assistant_id):
                async def toggle_callback(interaction: discord.Interaction):
                    success = await self.assistant_system.toggle_assistant_active(assistant_id, interaction.user.id)
                    
                    if success:
                        await interaction.response.send_message("已更新助理狀態！請使用 `/my_assistants` 查看最新狀態。", ephemeral=True)
                    else:
                        await interaction.response.send_message("更新狀態失敗！", ephemeral=True)
                
                return toggle_callback
            
            button.callback = await create_toggle_callback(assistant_id)
            view.add_item(button)
        
        await interaction.response.send_message(embed=embed, view=view)
    
    @app_commands.command(name="assistant_details", description="查看交易助理詳情")
    @app_commands.describe(assistant_id="助理ID")
    async def assistant_details(self, interaction: discord.Interaction, assistant_id: int):
        """查看交易助理詳情"""
        details = await self.assistant_system.get_assistant_details(assistant_id)
        
        if not details or details['user_id'] != interaction.user.id:
            await interaction.response.send_message("找不到該助理或你沒有權限查看！", ephemeral=True)
            return
        
        rarity_colors = {
            'N': discord.Color.light_grey(),
            'R': discord.Color.blue(),
            'SR': discord.Color.purple(),
            'SSR': discord.Color.gold()
        }
        
        rarity_emojis = {
            'N': '⚪',
            'R': '🔵',
            'SR': '🟣',
            'SSR': '🟡'
        }
        
        embed = discord.Embed(
            title=f"{rarity_emojis[details['rarity']]} {details['assistant_name']} 詳情",
            description=f"{'✅ 活躍中' if details['active'] else '⏸️ 未啟用'} | ID: {details['assistant_id']}",
            color=rarity_colors[details['rarity']]
        )
        
        # 添加監控的股票
        stocks_text = "無" if not details['stocks'] else ", ".join(details['stocks'])
        embed.add_field(name="監控股票", value=stocks_text, inline=False)
        
        # 添加設定
        settings_text = "未設定"
        if details['settings']:
            settings_text = "\n".join([f"{k}: {v}" for k, v in details['settings'].items()])
        
        embed.add_field(name="當前設定", value=settings_text, inline=False)
        
        # 添加交易記錄
        trades_text = "尚無交易記錄"
        if details['trades']:
            trades_list = []
            for trade_type, stock_code, shares, price, total_amount, profit_loss, trade_at in details['trades'][:5]:
                action = "買入" if trade_type == "buy" else "賣出"
                if trade_type == "sell" and profit_loss is not None:
                    profit_text = f"盈虧: {profit_loss:+,.2f}" if profit_loss != 0 else "盈虧: 0"
                else:
                    profit_text = ""
                
                trades_list.append(f"{trade_at}: {action} {stock_code} {shares}股 @ {price} ({profit_text})")
            
            trades_text = "\n".join(trades_list)
        
        embed.add_field(name="最近交易", value=trades_text, inline=False)
        
        # 添加總收益
        embed.add_field(name="總收益", value=f"{details['total_profit']:+,.2f} Silva幣", inline=False)
        
        # 創建設定按鈕
        view = discord.ui.View(timeout=180)
        
        # 添加監控股票按鈕
        stocks_button = discord.ui.Button(label="設定監控股票", style=discord.ButtonStyle.primary)
        
        async def stocks_callback(interaction: discord.Interaction):
            # 創建一個模態對話框
            modal = StocksSettingModal(details['assistant_id'], details['rarity'])
            await interaction.response.send_modal(modal)
        
        stocks_button.callback = stocks_callback
        view.add_item(stocks_button)
        
        # 添加交易設定按鈕
        settings_button = discord.ui.Button(label="設定交易策略", style=discord.ButtonStyle.primary)
        
        async def settings_callback(interaction: discord.Interaction):
            # 創建一個模態對話框
            modal = StrategySettingModal(details['assistant_id'], details['rarity'])
            await interaction.response.send_modal(modal)
        
        settings_button.callback = settings_callback
        view.add_item(settings_button)
        
        # 添加切換狀態按鈕
        toggle_button = discord.ui.Button(
            label="停用助理" if details['active'] else "啟用助理",
            style=discord.ButtonStyle.red if details['active'] else discord.ButtonStyle.green
        )
        
        async def toggle_callback(interaction: discord.Interaction):
            success = await self.assistant_system.toggle_assistant_active(details['assistant_id'], interaction.user.id)
            
            if success:
                new_status = not details['active']
                await interaction.response.send_message(
                    f"已{'停用' if not new_status else '啟用'}助理！請使用 `/assistant_details` 查看最新狀態。", 
                    ephemeral=True
                )
            else:
                await interaction.response.send_message("更新狀態失敗！", ephemeral=True)
        
        toggle_button.callback = toggle_callback
        view.add_item(toggle_button)
        
        await interaction.response.send_message(embed=embed, view=view)


class StocksSettingModal(discord.ui.Modal):
    """股票設定模態對話框"""
    def __init__(self, assistant_id, rarity):
        super().__init__(title="設定監控股票")
        self.assistant_id = assistant_id
        self.rarity = rarity
        
        # 根據稀有度決定可監控的股票數量
        max_stocks = {
            'N': 1,
            'R': 3,
            'SR': 5,
            'SSR': 10  # 實際不限制
        }
        
        self.stocks_input = discord.ui.TextInput(
            label=f"股票代號 (最多{max_stocks[rarity]}支，用逗號分隔)",
            placeholder="例如: AAPL, GOOG, TSLA",
            style=discord.TextStyle.short,
            max_length=100,
            required=True
        )
        self.add_item(self.stocks_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        # 解析股票代號
        stock_codes = [code.strip().upper() for code in self.stocks_input.value.split(',')]
        
        # 檢查股票是否存在
        stock_system = Stock(interaction.client)
        valid_stocks = []
        
        for code in stock_codes:
            if not code:
                continue
                
            stock_info = await stock_system.get_stock_info(code)
            if stock_info:
                valid_stocks.append(code)
        
        # 檢查股票數量是否超過限制
        max_stocks = {
            'N': 1,
            'R': 3,
            'SR': 5,
            'SSR': 100  # 實際不限制
        }
        
        if len(valid_stocks) > max_stocks[self.rarity]:
            await interaction.response.send_message(
                f"設定失敗！{self.rarity}級助理最多只能監控{max_stocks[self.rarity]}支股票。",
                ephemeral=True
            )
            return
        
        # 更新設定
        assistant_system = TradingAssistantSystem(interaction.client)
        success = await assistant_system.update_assistant_stocks(
            self.assistant_id,
            interaction.user.id,
            valid_stocks
        )
        
        if success:
            await interaction.response.send_message(
                f"已成功更新監控股票：{', '.join(valid_stocks)}",
                ephemeral=False
            )
        else:
            await interaction.response.send_message("更新設定失敗！", ephemeral=True)


class StrategySettingModal(discord.ui.Modal):
    """策略設定模態對話框"""
    def __init__(self, assistant_id, rarity):
        super().__init__(title="設定交易策略")
        self.assistant_id = assistant_id
        self.rarity = rarity
        
        # 根據稀有度添加不同的設定選項
        if rarity == 'N':
            self.buy_threshold = discord.ui.TextInput(
                label="買入價格門檻",
                placeholder="低於此價格時買入 (0表示不設定)",
                style=discord.TextStyle.short,
                required=True
            )
            self.add_item(self.buy_threshold)
            
            self.sell_threshold = discord.ui.TextInput(
                label="賣出價格門檻",
                placeholder="高於此價格時賣出 (0表示不設定)",
                style=discord.TextStyle.short,
                required=True
            )
            self.add_item(self.sell_threshold)
            
            self.trade_percentage = discord.ui.TextInput(
                label="交易資金比例 (%)",
                placeholder="每次交易使用的資金比例 (1-100)",
                style=discord.TextStyle.short,
                required=True,
                default="10"
            )
            self.add_item(self.trade_percentage)
            
        elif rarity == 'R':
            self.buy_threshold = discord.ui.TextInput(
                label="買入價格門檻",
                placeholder="低於此價格時買入 (0表示不設定)",
                style=discord.TextStyle.short,
                required=True
            )
            self.add_item(self.buy_threshold)
            
            self.sell_threshold = discord.ui.TextInput(
                label="賣出價格門檻",
                placeholder="高於此價格時賣出 (0表示不設定)",
                style=discord.TextStyle.short,
                required=True
            )
            self.add_item(self.sell_threshold)
            
            self.stop_loss = discord.ui.TextInput(
                label="止損點 (%)",
                placeholder="虧損超過此百分比時賣出 (0表示不設定)",
                style=discord.TextStyle.short,
                required=True,
                default="5"
            )
            self.add_item(self.stop_loss)
            
            self.ma_settings = discord.ui.TextInput(
                label="移動平均線設定",
                placeholder="短期/長期 (例如: 5/20)",
                style=discord.TextStyle.short,
                required=True,
                default="5/20"
            )
            self.add_item(self.ma_settings)
            
            self.trade_percentage = discord.ui.TextInput(
                label="交易資金比例 (%)",
                placeholder="每次交易使用的資金比例 (1-100)",
                style=discord.TextStyle.short,
                required=True,
                default="15"
            )
            self.add_item(self.trade_percentage)
            
        elif rarity == 'SR':
            self.indicators = discord.ui.TextInput(
                label="使用技術指標",
                placeholder="rsi:true,macd:true,pattern:true",
                style=discord.TextStyle.short,
                required=True,
                default="rsi:true,macd:true,pattern:true"
            )
            self.add_item(self.indicators)
            
            self.rsi_levels = discord.ui.TextInput(
                label="RSI買賣設定",
                placeholder="買入/賣出 (例如: 30/70)",
                style=discord.TextStyle.short,
                required=True,
                default="30/70"
            )
            self.add_item(self.rsi_levels)
            
            self.risk_reward = discord.ui.TextInput(
                label="風險報酬比",
                placeholder="越高風險越大收益越高 (1-5)",
                style=discord.TextStyle.short,
                required=True,
                default="2"
            )
            self.add_item(self.risk_reward)
            
            self.trade_percentage = discord.ui.TextInput(
                label="交易資金比例 (%)",
                placeholder="每次交易使用的資金比例 (1-100)",
                style=discord.TextStyle.short,
                required=True,
                default="20"
            )
            self.add_item(self.trade_percentage)
            
            self.trading_time = discord.ui.TextInput(
                label="交易時段",
                placeholder="all,morning,afternoon,evening",
                style=discord.TextStyle.short,
                required=True,
                default="all"
            )
            self.add_item(self.trading_time)
            
        elif rarity == 'SSR':
            self.strategy_type = discord.ui.TextInput(
                label="策略類型",
                placeholder="balanced,aggressive,conservative",
                style=discord.TextStyle.short,
                required=True,
                default="balanced"
            )
            self.add_item(self.strategy_type)
            
            self.risk_level = discord.ui.TextInput(
                label="風險水平",
                placeholder="0.1-1.0 (0.1最保守，1.0最激進)",
                style=discord.TextStyle.short,
                required=True,
                default="0.5"
            )
            self.add_item(self.risk_level)
            
            self.advanced_settings = discord.ui.TextInput(
                label="高級設定",
                placeholder="use_sentiment:true,auto_balance:true",
                style=discord.TextStyle.short,
                required=True,
                default="use_sentiment:true,auto_balance:true"
            )
            self.add_item(self.advanced_settings)
            
            self.trade_percentage = discord.ui.TextInput(
                label="交易資金比例 (%)",
                placeholder="每次交易使用的資金比例 (1-100)",
                style=discord.TextStyle.short,
                required=True,
                default="25"
            )
            self.add_item(self.trade_percentage)
            
            self.trading_frequency = discord.ui.TextInput(
                label="交易頻率",
                placeholder="hourly,every_2_hours,every_4_hours,daily",
                style=discord.TextStyle.short,
                required=True,
                default="hourly"
            )
            self.add_item(self.trading_frequency)
    
    async def on_submit(self, interaction: discord.Interaction):
        # 解析設定
        settings = {}
        
        if self.rarity == 'N':
            try:
                settings['buy_threshold'] = float(self.buy_threshold.value)
                settings['sell_threshold'] = float(self.sell_threshold.value)
                settings['trade_percentage'] = float(self.trade_percentage.value)
            except ValueError:
                await interaction.response.send_message("設定失敗！請輸入有效的數值。", ephemeral=True)
                return
                
        elif self.rarity == 'R':
            try:
                settings['buy_threshold'] = float(self.buy_threshold.value)
                settings['sell_threshold'] = float(self.sell_threshold.value)
                settings['stop_loss'] = float(self.stop_loss.value)
                settings['trade_percentage'] = float(self.trade_percentage.value)
                
                ma_values = self.ma_settings.value.split('/')
                if len(ma_values) == 2:
                    settings['ma_short'] = int(ma_values[0])
                    settings['ma_long'] = int(ma_values[1])
                else:
                    raise ValueError("移動平均線設定格式不正確")
            except ValueError as e:
                await interaction.response.send_message(f"設定失敗！{str(e)}", ephemeral=True)
                return
                
        elif self.rarity == 'SR':
            try:
                # 解析技術指標設定
                for item in self.indicators.value.split(','):
                    if ':' in item:
                        key, value = item.split(':')
                        settings[key.strip()] = value.strip()
                
                # 解析RSI設定
                rsi_values = self.rsi_levels.value.split('/')
                if len(rsi_values) == 2:
                    settings['rsi_buy'] = float(rsi_values[0])
                    settings['rsi_sell'] = float(rsi_values[1])
                else:
                    raise ValueError("RSI設定格式不正確")
                
                settings['risk_reward'] = float(self.risk_reward.value)
                settings['trade_percentage'] = float(self.trade_percentage.value)
                settings['trading_time'] = self.trading_time.value
            except ValueError as e:
                await interaction.response.send_message(f"設定失敗！{str(e)}", ephemeral=True)
                return
                
        elif self.rarity == 'SSR':
            try:
                settings['strategy_type'] = self.strategy_type.value
                settings['risk_level'] = float(self.risk_level.value)
                settings['trade_percentage'] = float(self.trade_percentage.value)
                settings['trading_frequency'] = self.trading_frequency.value
                
                # 解析高級設定
                for item in self.advanced_settings.value.split(','):
                    if ':' in item:
                        key, value = item.split(':')
                        settings[key.strip()] = value.strip()
            except ValueError as e:
                await interaction.response.send_message(f"設定失敗！{str(e)}", ephemeral=True)
                return
        
        # 更新設定
        assistant_system = TradingAssistantSystem(interaction.client)
        success = await assistant_system.update_assistant_settings(
            self.assistant_id,
            interaction.user.id,
            settings
        )
        
        if success:
            await interaction.response.send_message(
                "已成功更新交易策略設定！",
                ephemeral=False
            )
        else:
            await interaction.response.send_message("更新設定失敗！", ephemeral=True)


async def setup(bot):
    await bot.add_cog(TradingAssistantCog(bot))