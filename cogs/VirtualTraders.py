import discord
from discord.ext import commands, tasks
from discord import app_commands
import random
import asyncio
import datetime
from typing import List, Dict, Tuple, Optional
from models.stocks import Stock
from models.currency import Currency
from utils.database import get_db_connection, execute_query

class VirtualTrader:
    """虛擬交易者模型"""
    
    def __init__(self, trader_id: int, name: str, balance: int = 50000, strategy: str = "random", risk_level: float = 0.5, active: bool = True):
        self.trader_id = trader_id
        self.name = name
        self.balance = balance
        self.strategy = strategy
        self.risk_level = risk_level
        self.active = active
        self.last_trade_time = None

class TradeStrategy:
    """交易策略基類"""
    
    @staticmethod
    async def decide_action(trader: VirtualTrader, stock_info: dict, price_history: list, holdings: int = 0) -> Tuple[str, int, float]:
        """
        決定交易行為
        返回: (action, shares, price)，其中action可以是"buy", "sell"或"hold"
        """
        return "hold", 0, 0

class RandomStrategy(TradeStrategy):
    """隨機交易策略"""
    
    @staticmethod
    async def decide_action(trader: VirtualTrader, stock_info: dict, price_history: list, holdings: int = 0) -> Tuple[str, int, float]:
        current_price = stock_info['price']
        total_shares = stock_info['total_shares']
        
        # 隨機決定行為
        action = random.choices(["buy", "sell", "hold"], weights=[0.4, 0.4, 0.2])[0]
        
        # 如果沒有持股，不能賣出
        if action == "sell" and holdings <= 0:
            action = "buy"
        
        # 如果餘額不足，不能買入
        if action == "buy" and trader.balance < current_price:
            action = "hold"
        
        if action == "buy":
            # 決定買入數量和價格，限制最大買入量為總股數的0.5%
            max_affordable = max(1, int(trader.balance * trader.risk_level / current_price))
            max_allowed = max(1, int(total_shares * 0.005))  # 總股數的0.5%
            max_shares = min(max_affordable, max_allowed)
            shares = random.randint(1, max_shares)
            
            # 決定買入價格，在當前價格的±5%範圍內，四捨五入到小數點後2位
            price_variation = random.uniform(-0.05, 0.05)
            price = round(current_price * (1 + price_variation), 2)
            
            return "buy", shares, price
            
        elif action == "sell":
            # 決定賣出數量
            shares = random.randint(1, holdings)
            
            # 決定賣出價格，在當前價格的±5%範圍內，四捨五入到小數點後2位
            price_variation = random.uniform(-0.05, 0.05)
            price = round(current_price * (1 + price_variation), 2)
            
            return "sell", shares, price
            
        return "hold", 0, 0

class TrendFollowingStrategy(TradeStrategy):
    """趨勢跟蹤策略"""
    
    @staticmethod
    async def decide_action(trader: VirtualTrader, stock_info: dict, price_history: list, holdings: int = 0) -> Tuple[str, int, float]:
        if not price_history or len(price_history) < 5:
            return "hold", 0, 0
            
        current_price = stock_info['price']
        total_shares = stock_info['total_shares']
        
        # 計算短期和長期移動平均線
        prices = [price for _, price in price_history]
        prices.reverse()  # 從舊到新排序
        
        short_ma = sum(prices[-5:]) / 5 if len(prices) >= 5 else current_price
        long_ma = sum(prices[-10:]) / 10 if len(prices) >= 10 else current_price
        
        # 趨勢判斷
        if short_ma > long_ma * 1.02:  # 上升趨勢，買入
            action = "buy"
        elif short_ma < long_ma * 0.98:  # 下降趨勢，賣出
            action = "sell"
        else:  # 橫盤，持有
            action = "hold"
        
        # 如果沒有持股，不能賣出
        if action == "sell" and holdings <= 0:
            action = "hold"
        
        # 如果餘額不足，不能買入
        if action == "buy" and trader.balance < current_price:
            action = "hold"
        
        if action == "buy":
            # 決定買入數量和價格，限制最大買入量為總股數的0.5%
            max_affordable = max(1, int(trader.balance * trader.risk_level / current_price))
            max_allowed = max(1, int(total_shares * 0.005))  # 總股數的0.5%
            max_shares = min(max_affordable, max_allowed)
            shares = random.randint(1, max_shares)
            
            # 買入價格接近當前價格，四捨五入到小數點後2位
            price_variation = random.uniform(-0.02, 0.02)
            price = round(current_price * (1 + price_variation), 2)
            
            return "buy", shares, price
            
        elif action == "sell":
            # 決定賣出數量
            shares = random.randint(1, holdings)
            
            # 賣出價格接近當前價格，四捨五入到小數點後2位
            price_variation = random.uniform(-0.02, 0.02)
            price = round(current_price * (1 + price_variation), 2)
            
            return "sell", shares, price
            
        return "hold", 0, 0

class ReverseStrategy(TradeStrategy):
    """反向交易策略"""
    
    @staticmethod
    async def decide_action(trader: VirtualTrader, stock_info: dict, price_history: list, holdings: int = 0) -> Tuple[str, int, float]:
        if not price_history or len(price_history) < 5:
            return "hold", 0, 0
            
        current_price = stock_info['price']
        total_shares = stock_info['total_shares']
        
        # 計算近期漲跌幅
        prices = [price for _, price in price_history]
        prices.reverse()  # 從舊到新排序
        
        price_change = (prices[-1] / prices[-5] - 1) if len(prices) >= 5 else 0
        
        # 反向策略：價格大幅上漲則賣出，大幅下跌則買入
        if price_change > 0.05:  # 上漲超過5%，賣出
            action = "sell"
        elif price_change < -0.05:  # 下跌超過5%，買入
            action = "buy"
        else:  # 價格波動不大，持有
            action = "hold"
        
        # 如果沒有持股，不能賣出
        if action == "sell" and holdings <= 0:
            action = "hold"
        
        # 如果餘額不足，不能買入
        if action == "buy" and trader.balance < current_price:
            action = "hold"
        
        if action == "buy":
            # 決定買入數量和價格，限制最大買入量為總股數的0.5%
            max_affordable = max(1, int(trader.balance * trader.risk_level / current_price))
            max_allowed = max(1, int(total_shares * 0.005))  # 總股數的0.5%
            max_shares = min(max_affordable, max_allowed)
            shares = random.randint(1, max_shares)
            
            # 買入價格略低於當前價格，四捨五入到小數點後2位
            price_variation = random.uniform(-0.04, -0.01)
            price = round(current_price * (1 + price_variation), 2)
            
            return "buy", shares, price
            
        elif action == "sell":
            # 決定賣出數量
            shares = random.randint(1, holdings)
            
            # 賣出價格略高於當前價格，四捨五入到小數點後2位
            price_variation = random.uniform(0.01, 0.04)
            price = round(current_price * (1 + price_variation), 2)
            
            return "sell", shares, price
            
        return "hold", 0, 0

class VirtualTraderManager:
    """虛擬交易者管理系統"""
    
    def __init__(self, bot):
        self.bot = bot
        self.db_name = "virtual_traders"
        self.traders = {}  # {trader_id: VirtualTrader}
        self.stock_system = Stock(bot)
        self.loaded = False
        
    async def setup_database(self):
        """初始化資料庫表格"""
        conn = await get_db_connection(self.db_name)
        cursor = await conn.cursor()
        
        # 虛擬交易者表格
        await cursor.execute('''
        CREATE TABLE IF NOT EXISTS virtual_traders (
            trader_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            balance INTEGER DEFAULT 50000,
            strategy TEXT DEFAULT 'random',
            risk_level REAL DEFAULT 0.5,
            active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 虛擬交易者交易記錄表格
        await cursor.execute('''
        CREATE TABLE IF NOT EXISTS virtual_trades (
            trade_id INTEGER PRIMARY KEY AUTOINCREMENT,
            trader_id INTEGER,
            stock_code TEXT,
            action TEXT,
            shares INTEGER,
            price REAL,
            total_amount REAL,
            trade_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (trader_id) REFERENCES virtual_traders(trader_id)
        )
        ''')
        
        await conn.commit()
        
    async def load_traders(self):
        """從資料庫加載所有虛擬交易者"""
        if self.loaded:
            return
            
        await self.setup_database()
        
        query = '''
        SELECT trader_id, name, balance, strategy, risk_level, active
        FROM virtual_traders
        '''
        
        result = await execute_query(self.db_name, query, fetch_type='all')
        
        if result:
            for trader_id, name, balance, strategy, risk_level, active in result:
                self.traders[trader_id] = VirtualTrader(
                    trader_id=trader_id,
                    name=name,
                    balance=balance,
                    strategy=strategy,
                    risk_level=risk_level,
                    active=bool(active)
                )
                
        self.loaded = True
        
    async def create_trader(self, name: str, balance: int = 50000, strategy: str = None, risk_level: float = None) -> int:
        """創建一個新的虛擬交易者"""
        await self.setup_database()
        
        # 如果未指定策略，隨機選擇一個
        if strategy is None:
            strategy = random.choice(["random", "trend", "reverse"])
            
        # 如果未指定風險等級，隨機生成一個
        if risk_level is None:
            risk_level = random.uniform(0.1, 1.0)
            
        query = '''
        INSERT INTO virtual_traders (name, balance, strategy, risk_level)
        VALUES (?, ?, ?, ?)
        '''
        
        trader_id = await execute_query(self.db_name, query, (name, balance, strategy, risk_level))
        
        if trader_id:
            # 加載到內存
            self.traders[trader_id] = VirtualTrader(
                trader_id=trader_id,
                name=name,
                balance=balance,
                strategy=strategy,
                risk_level=risk_level
            )
            
            # 在 Currency 系統中設置相同的餘額
            currency = Currency(self.bot)
            await currency.update_balance(trader_id, balance, f"初始化虛擬交易者 {name} 資金")
            
        return trader_id
        
    async def get_all_traders(self) -> List[VirtualTrader]:
        """獲取所有虛擬交易者"""
        await self.load_traders()
        return list(self.traders.values())
        
    async def get_trader(self, trader_id: int) -> Optional[VirtualTrader]:
        """獲取指定ID的虛擬交易者"""
        await self.load_traders()
        return self.traders.get(trader_id)
        
    async def update_trader_balance(self, trader_id: int, amount: int):
        """更新虛擬交易者餘額"""
        trader = await self.get_trader(trader_id)
        if not trader:
            return False
            
        trader.balance += amount
        
        query = '''
        UPDATE virtual_traders
        SET balance = ?
        WHERE trader_id = ?
        '''
        
        await execute_query(self.db_name, query, (trader.balance, trader_id))
        
        return True
    
    async def sync_trader_balance(self, trader_id: int):
        """同步虛擬交易者在Currency系統中的餘額"""
        trader = await self.get_trader(trader_id)
        if trader:
            currency = Currency(self.bot)
            current_balance = await currency.get_balance(trader_id)
            delta = trader.balance - current_balance
            if delta != 0:
                await currency.update_balance(trader_id, delta, f"同步虛擬交易者 {trader.name} 餘額")
                return True
        return False
        
    async def toggle_trader_active(self, trader_id: int) -> bool:
        """切換虛擬交易者的活躍狀態"""
        trader = await self.get_trader(trader_id)
        if not trader:
            return False
            
        trader.active = not trader.active
        
        query = '''
        UPDATE virtual_traders
        SET active = ?
        WHERE trader_id = ?
        '''
        
        await execute_query(self.db_name, query, (int(trader.active), trader_id))
        
        return True
        
    async def update_trader_strategy(self, trader_id: int, strategy: str) -> bool:
        """更新虛擬交易者的交易策略"""
        trader = await self.get_trader(trader_id)
        if not trader:
            return False
            
        valid_strategies = ["random", "trend", "reverse"]
        if strategy not in valid_strategies:
            return False
            
        trader.strategy = strategy
        
        query = '''
        UPDATE virtual_traders
        SET strategy = ?
        WHERE trader_id = ?
        '''
        
        await execute_query(self.db_name, query, (strategy, trader_id))
        
        return True
        
    async def get_trader_holdings(self, trader_id: int) -> Dict[str, int]:
        """獲取虛擬交易者的持股情況 - 直接從股票系統獲取真實持股"""
        try:
            # 直接從股票系統獲取用戶真實持股
            user_stocks = await self.stock_system.get_user_stocks(trader_id)
            
            holdings = {}
            if user_stocks:
                for stock_id, code, name, shares, price in user_stocks:
                    holdings[code] = shares
                    
            return holdings
        except Exception as e:
            print(f"獲取虛擬交易者持股時發生錯誤: {e}")
            return {}
            
    async def record_trade(self, trader_id: int, stock_code: str, action: str, shares: int, price: float, total_amount: float):
        """記錄交易"""
        query = '''
        INSERT INTO virtual_trades (trader_id, stock_code, action, shares, price, total_amount)
        VALUES (?, ?, ?, ?, ?, ?)
        '''
        
        await execute_query(
            self.db_name,
            query,
            (trader_id, stock_code, action, shares, price, total_amount)
        )
        
    async def execute_trader_action(self, trader: VirtualTrader):
        """執行單個交易者的交易行為"""
        # 獲取所有股票
        stocks = await self.stock_system.get_all_stocks()
        if not stocks:
            return
        
        # 隨機選擇一支股票
        stock_id, code, name, price, total_shares, issuer_id = random.choice(stocks)
        
        # 獲取股票詳情
        stock_info = await self.stock_system.get_stock_info(code)
        if not stock_info:
            return
        
        # 獲取價格歷史
        price_history = await self.stock_system.get_price_history(code, 30)
        
        # 獲取持股情況 - 直接從股票系統獲取真實持股
        holdings = await self.get_trader_holdings(trader.trader_id)
        current_shares = holdings.get(code, 0)
        
        # 根據交易者的策略決定行為
        strategy_map = {
            "random": RandomStrategy,
            "trend": TrendFollowingStrategy,
            "reverse": ReverseStrategy
        }
        
        strategy_class = strategy_map.get(trader.strategy, RandomStrategy)
        action, shares, price = await strategy_class.decide_action(trader, stock_info, price_history, current_shares)
        
        if action == "hold" or shares <= 0:
            return
            
        # 執行交易
        if action == "buy":
            total_cost = shares * price
            
            # 檢查餘額
            if trader.balance < total_cost:
                return
                
            try:
                # 扣除資金
                await self.update_trader_balance(trader.trader_id, -int(total_cost))
                
                # 添加委託單
                success, message = await self.stock_system.place_order(
                    trader.trader_id, 
                    code, 
                    "buy", 
                    shares, 
                    price
                )
                
                if success:
                    # 記錄交易
                    await self.record_trade(
                        trader.trader_id, 
                        code, 
                        "buy", 
                        shares, 
                        price, 
                        total_cost
                    )
                    
                    print(f"虛擬交易者 {trader.name} 成功下單購買 {shares} 股 {code} @ {price}")
                else:
                    # 如果下單失敗，退還資金
                    await self.update_trader_balance(trader.trader_id, int(total_cost))
                    print(f"虛擬交易者 {trader.name} 下單失敗: {message}")
            except Exception as e:
                # 發生錯誤，確保退還資金
                await self.update_trader_balance(trader.trader_id, int(total_cost))
                print(f"虛擬交易者 {trader.name} 下單時發生錯誤: {e}")
                
        elif action == "sell" and current_shares > 0:
            # 確保不會賣出超過持有量
            shares = min(shares, current_shares)
            
            if shares <= 0:
                return
                
            try:
                # 添加委託單
                success, message = await self.stock_system.place_order(
                    trader.trader_id, 
                    code, 
                    "sell", 
                    shares, 
                    price
                )
                
                if success:
                    # 記錄交易
                    total_amount = shares * price
                    await self.record_trade(
                        trader.trader_id, 
                        code, 
                        "sell", 
                        shares, 
                        price, 
                        total_amount
                    )
                    print(f"虛擬交易者 {trader.name} 成功下單出售 {shares} 股 {code} @ {price}")
                else:
                    print(f"虛擬交易者 {trader.name} 下單失敗: {message}")
            except Exception as e:
                print(f"虛擬交易者 {trader.name} 下單時發生錯誤: {e}")
        
        # 更新最後交易時間
        trader.last_trade_time = datetime.datetime.now()
        
    async def execute_trades(self):
        """執行所有活躍交易者的交易操作"""
        await self.load_traders()
        
        active_traders = [t for t in self.traders.values() if t.active]
        if not active_traders:
            return
            
        # 隨機選擇部分交易者進行交易
        traders_to_trade = random.sample(
            active_traders,
            min(len(active_traders), random.randint(1, max(1, len(active_traders) // 3)))
        )
        
        for trader in traders_to_trade:
            try:
                await self.execute_trader_action(trader)
            except Exception as e:
                print(f"執行交易者 {trader.name} 的交易時發生錯誤: {e}")
                
    async def get_trader_stats(self) -> Dict:
        """獲取虛擬交易者的統計信息"""
        stats = {
            "total": 0,
            "active": 0,
            "inactive": 0,
            "strategies": {
                "random": 0,
                "trend": 0,
                "reverse": 0
            },
            "total_balance": 0,
            "total_holdings_value": 0
        }
        
        await self.load_traders()
        
        for trader in self.traders.values():
            stats["total"] += 1
            if trader.active:
                stats["active"] += 1
            else:
                stats["inactive"] += 1
                
            stats["strategies"][trader.strategy] += 1
            stats["total_balance"] += trader.balance
            
            # 計算持股價值
            holdings = await self.get_trader_holdings(trader.trader_id)
            for stock_code, shares in holdings.items():
                stock_info = await self.stock_system.get_stock_info(stock_code)
                if stock_info:
                    stats["total_holdings_value"] += shares * stock_info["price"]
                    
        return stats

class VirtualTradersCog(commands.Cog):
    """虛擬交易者系統指令"""

    def __init__(self, bot):
        self.bot = bot
        self.manager = VirtualTraderManager(bot)
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
                # 執行交易
                await self.manager.execute_trades()
                
                # 等待一段時間
                wait_time = random.randint(180, 600)  # 3-10分鐘
                await asyncio.sleep(wait_time)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"交易循環任務發生錯誤: {e}")
                await asyncio.sleep(60)  # 發生錯誤後等待1分鐘
    
    @app_commands.command(name="createvirtualtraders", description="創建虛擬交易者 (管理員專用)")
    @app_commands.default_permissions(administrator=True)
    async def create_virtual_traders(self, interaction: discord.Interaction, count: int = 5):
        """創建虛擬交易者"""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("你沒有權限使用此指令！", ephemeral=True)
            return
            
        # 創建虛擬交易者
        created = 0
        for i in range(count):
            trader_name = f"虛擬交易者{random.randint(1000, 9999)}"
            await self.manager.create_trader(trader_name)
            created += 1
            
        await interaction.response.send_message(f"✅ 已創建 {created} 個虛擬交易者！", ephemeral=False)
    
    @app_commands.command(name="listvirtualtraders", description="列出所有虛擬交易者 (管理員專用)")
    @app_commands.default_permissions(administrator=True)
    async def list_virtual_traders(self, interaction: discord.Interaction):
        """列出所有虛擬交易者"""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("你沒有權限使用此指令！", ephemeral=True)
            return
            
        # 獲取所有交易者
        traders = await self.manager.get_all_traders()
        
        if not traders:
            await interaction.response.send_message("目前沒有任何虛擬交易者！", ephemeral=True)
            return
            
        embed = discord.Embed(
            title="🤖 虛擬交易者列表",
            description=f"共有 {len(traders)} 個虛擬交易者",
            color=discord.Color.blue()
        )
        
        # 顯示前10個交易者
        for trader in traders[:10]:
            embed.add_field(
                name=f"{trader.name} (ID: {trader.trader_id})",
                value=f"餘額: {trader.balance:,} Silva幣\n策略: {trader.strategy}\n狀態: {'活躍' if trader.active else '停用'}",
                inline=True
            )
            
        # 顯示統計信息
        stats = await self.manager.get_trader_stats()
        
        embed.add_field(
            name="統計信息",
            value=f"活躍交易者: {stats['active']}/{stats['total']}\n"
                  f"隨機策略: {stats['strategies']['random']}\n"
                  f"趨勢跟蹤: {stats['strategies']['trend']}\n"
                  f"反向交易: {stats['strategies']['reverse']}\n"
                  f"總資金: {stats['total_balance']:,} Silva幣\n"
                  f"總持股價值: {stats['total_holdings_value']:,} Silva幣",
            inline=False
        )
            
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="togglevirtualtrader", description="開啟/關閉指定的虛擬交易者 (管理員專用)")
    @app_commands.describe(trader_id="交易者ID")
    @app_commands.default_permissions(administrator=True)
    async def toggle_virtual_trader(self, interaction: discord.Interaction, trader_id: int):
        """開啟/關閉指定的虛擬交易者"""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("你沒有權限使用此指令！", ephemeral=True)
            return
            
        success = await self.manager.toggle_trader_active(trader_id)
        
        if success:
            trader = await self.manager.get_trader(trader_id)
            status = "啟用" if trader.active else "停用"
            await interaction.response.send_message(f"✅ 已{status}虛擬交易者 {trader.name}！", ephemeral=False)
        else:
            await interaction.response.send_message("❌ 找不到指定的虛擬交易者！", ephemeral=True)
    
    @app_commands.command(name="updatetraderstrategy", description="更新虛擬交易者的策略 (管理員專用)")
    @app_commands.describe(trader_id="交易者ID", strategy="策略 (random, trend, reverse)")
    @app_commands.default_permissions(administrator=True)
    async def update_trader_strategy(self, interaction: discord.Interaction, trader_id: int, strategy: str):
        """更新虛擬交易者的策略"""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("你沒有權限使用此指令！", ephemeral=True)
            return
            
        valid_strategies = ["random", "trend", "reverse"]
        if strategy not in valid_strategies:
            await interaction.response.send_message(f"❌ 無效的策略！有效選項: {', '.join(valid_strategies)}", ephemeral=True)
            return
            
        success = await self.manager.update_trader_strategy(trader_id, strategy)
        
        if success:
            trader = await self.manager.get_trader(trader_id)
            await interaction.response.send_message(f"✅ 已將虛擬交易者 {trader.name} 的策略更新為 {strategy}！", ephemeral=False)
        else:
            await interaction.response.send_message("❌ 找不到指定的虛擬交易者！", ephemeral=True)
    
    @app_commands.command(name="traderdetails", description="查看虛擬交易者詳情 (管理員專用)")
    @app_commands.describe(trader_id="交易者ID")
    @app_commands.default_permissions(administrator=True)
    async def trader_details(self, interaction: discord.Interaction, trader_id: int):
        """查看虛擬交易者詳情"""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("你沒有權限使用此指令！", ephemeral=True)
            return
            
        trader = await self.manager.get_trader(trader_id)
        
        if not trader:
            await interaction.response.send_message("❌ 找不到指定的虛擬交易者！", ephemeral=True)
            return
            
        # 獲取持股情況
        holdings = await self.manager.get_trader_holdings(trader_id)
        
        embed = discord.Embed(
            title=f"🤖 {trader.name} 詳情",
            description=f"ID: {trader.trader_id} | 狀態: {'活躍' if trader.active else '停用'}",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="餘額", value=f"{trader.balance:,} Silva幣", inline=True)
        embed.add_field(name="策略", value=trader.strategy, inline=True)
        embed.add_field(name="風險等級", value=f"{trader.risk_level:.2f}", inline=True)
        
        if not holdings:
            embed.add_field(name="持股", value="無", inline=False)
        else:
            holdings_text = ""
            total_value = 0
            
            for stock_code, shares in holdings.items():
                stock_info = await self.manager.stock_system.get_stock_info(stock_code)
                if stock_info:
                    value = shares * stock_info["price"]
                    total_value += value
                    holdings_text += f"{stock_code}: {shares}股 (價值: {value:,.2f} Silva幣)\n"
                else:
                    holdings_text += f"{stock_code}: {shares}股\n"
                    
            embed.add_field(name="持股", value=holdings_text, inline=False)
            embed.add_field(name="持股總價值", value=f"{total_value:,.2f} Silva幣", inline=False)
            
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="forcetrade", description="強制所有虛擬交易者立即交易 (管理員專用)")
    @app_commands.default_permissions(administrator=True)
    async def force_trade(self, interaction: discord.Interaction):
        """強制所有虛擬交易者立即交易"""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("你沒有權限使用此指令！", ephemeral=True)
            return
            
        await interaction.response.defer(thinking=True)
        
        try:
            # 執行交易
            await self.manager.execute_trades()
            
            await interaction.followup.send("✅ 已強制所有活躍的虛擬交易者進行交易！")
        except Exception as e:
            await interaction.followup.send(f"❌ 執行交易時發生錯誤: {str(e)}")
    
    @app_commands.command(name="virtualtradersstats", description="查看虛擬交易者統計信息 (管理員專用)")
    @app_commands.default_permissions(administrator=True)
    async def virtual_traders_stats(self, interaction: discord.Interaction):
        """查看虛擬交易者統計信息"""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("你沒有權限使用此指令！", ephemeral=True)
            return
            
        stats = await self.manager.get_trader_stats()
        
        embed = discord.Embed(
            title="📊 虛擬交易者統計信息",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="總數", value=str(stats['total']), inline=True)
        embed.add_field(name="活躍", value=str(stats['active']), inline=True)
        embed.add_field(name="停用", value=str(stats['inactive']), inline=True)
        
        embed.add_field(name="隨機策略", value=str(stats['strategies']['random']), inline=True)
        embed.add_field(name="趨勢跟蹤", value=str(stats['strategies']['trend']), inline=True)
        embed.add_field(name="反向交易", value=str(stats['strategies']['reverse']), inline=True)
        
        embed.add_field(name="總資金", value=f"{stats['total_balance']:,} Silva幣", inline=True)
        embed.add_field(name="總持股價值", value=f"{stats['total_holdings_value']:,} Silva幣", inline=True)
        embed.add_field(name="總資產", value=f"{stats['total_balance'] + stats['total_holdings_value']:,} Silva幣", inline=True)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="virtualorders", description="查看虛擬交易者的活躍委託單 (管理員專用)")
    @app_commands.default_permissions(administrator=True)
    async def virtual_orders(self, interaction: discord.Interaction):
        """查看虛擬交易者的活躍委託單"""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("你沒有權限使用此指令！", ephemeral=True)
            return
            
        # 獲取所有虛擬交易者
        traders = await self.manager.get_all_traders()
        
        if not traders:
            await interaction.response.send_message("目前沒有任何虛擬交易者！", ephemeral=True)
            return
        
        trader_ids = [trader.trader_id for trader in traders]
        
        # 獲取所有虛擬交易者的活躍委託單
        orders = []
        stock_system = Stock(self.bot)
        
        for trader_id in trader_ids:
            trader_orders = await stock_system.get_user_orders(trader_id, active_only=True)
            orders.extend([(trader_id, *order) for order in trader_orders])
        
        if not orders:
            await interaction.response.send_message("目前沒有任何虛擬交易者的活躍委託單！", ephemeral=True)
            return
            
        # 按交易者ID分組
        orders_by_trader = {}
        for trader_id, *order_data in orders:
            if trader_id not in orders_by_trader:
                orders_by_trader[trader_id] = []
            orders_by_trader[trader_id].append(order_data)
        
        # 創建嵌入訊息
        embeds = []
        
        for trader_id, trader_orders in orders_by_trader.items():
            trader = None
            for t in traders:
                if t.trader_id == trader_id:
                    trader = t
                    break
                    
            if not trader:
                continue
                
            embed = discord.Embed(
                title=f"🤖 {trader.name} 的委託單",
                description=f"交易者ID: {trader_id} | 餘額: {trader.balance:,} Silva幣",
                color=discord.Color.blue()
            )
            
            for order_id, stock_code, stock_name, order_type, shares, price, status, created_at in trader_orders[:5]:  # 只顯示前5個
                type_emoji = "🟢" if order_type == "buy" else "🔴"
                type_text = "購買" if order_type == "buy" else "出售"
                
                embed.add_field(
                    name=f"#{order_id}: {type_emoji} {type_text} {stock_code}",
                    value=f"股票: {stock_name}\n數量: {shares} 股\n價格: {price} Silva幣\n總額: {shares * price:,.2f} Silva幣\n狀態: {status}\n提交時間: {created_at}",
                    inline=True
                )
                
            embed.set_footer(text=f"共 {len(trader_orders)} 個委託單")
            embeds.append(embed)
        
        if not embeds:
            await interaction.response.send_message("無法獲取虛擬交易者的委託單信息！", ephemeral=True)
            return
            
        # 發送第一個嵌入訊息
        current_page = 0
        
        # 創建按鈕視圖
        view = discord.ui.View(timeout=180)
        
        # 添加上一頁按鈕
        previous_button = discord.ui.Button(label="上一頁", style=discord.ButtonStyle.primary, disabled=True)
        
        async def previous_callback(interaction: discord.Interaction):
            nonlocal current_page
            current_page -= 1
            
            # 更新按鈕狀態
            previous_button.disabled = current_page == 0
            next_button.disabled = current_page == len(embeds) - 1
            
            await interaction.response.edit_message(embed=embeds[current_page], view=view)
        
        previous_button.callback = previous_callback
        view.add_item(previous_button)
        
        # 添加下一頁按鈕
        next_button = discord.ui.Button(label="下一頁", style=discord.ButtonStyle.primary, disabled=len(embeds) == 1)
        
        async def next_callback(interaction: discord.Interaction):
            nonlocal current_page
            current_page += 1
            
            # 更新按鈕狀態
            previous_button.disabled = current_page == 0
            next_button.disabled = current_page == len(embeds) - 1
            
            await interaction.response.edit_message(embed=embeds[current_page], view=view)
        
        next_button.callback = next_callback
        view.add_item(next_button)
        
        # 修復了 view=None 錯誤，改為始終提供 view
        # 當只有一頁時，禁用兩個按鈕但仍然提供 view
        if len(embeds) == 1:
            previous_button.disabled = True
            next_button.disabled = True
            
        await interaction.response.send_message(embed=embeds[0], view=view)

    @app_commands.command(name="syncvirtualtraders", description="同步所有虛擬交易者的餘額 (管理員專用)")
    @app_commands.default_permissions(administrator=True)
    async def sync_virtual_traders(self, interaction: discord.Interaction):
        """同步所有虛擬交易者的餘額"""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("你沒有權限使用此指令！", ephemeral=True)
            return
            
        await interaction.response.defer(thinking=True)
        
        try:
            traders = await self.manager.get_all_traders()
            synced = 0
            
            for trader in traders:
                if await self.manager.sync_trader_balance(trader.trader_id):
                    synced += 1
                    
            await interaction.followup.send(f"✅ 已同步 {synced}/{len(traders)} 個虛擬交易者的餘額！")
        except Exception as e:
            await interaction.followup.send(f"❌ 同步餘額時發生錯誤: {str(e)}")


async def setup(bot):
    await bot.add_cog(VirtualTradersCog(bot))