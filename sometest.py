import random
import uuid
from datetime import datetime
from typing import Dict, List, Tuple, Optional

class CentralBank:
    """中央銀行類 - 追蹤所有貨幣流動"""
    
    def __init__(self, total_money: float):
        """初始化中央銀行，設定總貨幣量"""
        self.total_money = total_money
        self.current_circulation = 0  # 當前流通中的貨幣
        self.transaction_log = []
        
    def audit(self, users: List['User'], stock_market: 'StockMarket', gambling_system: 'GamblingSystem') -> bool:
        """審計系統，確保總貨幣量不變"""
        money_in_users = sum(user.balance for user in users)
        money_in_stock_market = stock_market.get_total_money()
        money_in_gambling = gambling_system.get_total_money()
        
        actual_total = money_in_users + money_in_stock_market + money_in_gambling
        
        if abs(actual_total - self.total_money) > 0.001:  # 允許浮點數計算的微小誤差
            print(f"警告：貨幣總量不一致！理論總量：{self.total_money}，實際總量：{actual_total}")
            difference = self.total_money - actual_total
            print(f"差額：{difference}")
            return False
        
        print(f"審計成功：總貨幣量 {self.total_money} 保持不變")
        print(f"用戶持有：{money_in_users}, 股市中：{money_in_stock_market}, 賭場中：{money_in_gambling}")
        return True
    
    def log_transaction(self, from_entity: str, to_entity: str, amount: float, transaction_type: str):
        """記錄所有交易"""
        self.transaction_log.append({
            'timestamp': datetime.now(),
            'from': from_entity,
            'to': to_entity,
            'amount': amount,
            'type': transaction_type
        })


class User:
    """用戶類 - 代表系統中的玩家或管理員"""
    
    def __init__(self, name: str, is_admin: bool = False, initial_balance: float = 0):
        """初始化用戶"""
        self.id = str(uuid.uuid4())
        self.name = name
        self.is_admin = is_admin
        self.balance = initial_balance
        self.stocks = {}  # 持有的股票 {公司ID: 數量}
        self.transaction_history = []
    
    def transfer_money(self, target_user: 'User', amount: float, central_bank: CentralBank) -> bool:
        """轉賬給另一個用戶"""
        if amount <= 0:
            print("錯誤：轉賬金額必須為正數")
            return False
            
        if self.balance < amount:
            print(f"錯誤：{self.name} 餘額不足，無法轉賬 {amount}")
            return False
        
        self.balance -= amount
        target_user.balance += amount
        
        transaction_record = {
            'timestamp': datetime.now(),
            'type': 'transfer',
            'amount': amount,
            'from': self.name,
            'to': target_user.name
        }
        
        self.transaction_history.append(transaction_record)
        target_user.transaction_history.append(transaction_record)
        
        # 記錄到中央銀行
        central_bank.log_transaction(self.name, target_user.name, amount, 'transfer')
        
        print(f"{self.name} 成功轉賬 {amount} 給 {target_user.name}")
        return True


class Stock:
    """股票類"""
    
    def __init__(self, name: str, initial_price: float, total_shares: int):
        """初始化股票"""
        self.id = str(uuid.uuid4())
        self.name = name
        self.price = initial_price
        self.total_shares = total_shares
        self.available_shares = total_shares  # 初始所有股票都可用
        self.price_history = [initial_price]
        self.dividend_rate = 0.02  # 股息率，例如2%
    
    def update_price(self, new_price: float):
        """更新股票價格"""
        self.price = new_price
        self.price_history.append(new_price)
    
    def calculate_market_cap(self) -> float:
        """計算市值"""
        return self.price * self.total_shares
    
    def pay_dividend(self, users: List[User], central_bank: CentralBank):
        """向股東支付股息"""
        for user in users:
            if self.id in user.stocks and user.stocks[self.id] > 0:
                shares_owned = user.stocks[self.id]
                dividend_amount = shares_owned * self.price * self.dividend_rate
                user.balance += dividend_amount
                
                # 記錄交易
                central_bank.log_transaction(
                    f"Stock:{self.name}", 
                    user.name, 
                    dividend_amount, 
                    'dividend'
                )
                
                print(f"{user.name} 收到 {self.name} 股票的股息 {dividend_amount}")


class StockMarket:
    """股票市場類"""
    
    def __init__(self, central_bank: CentralBank):
        """初始化股票市場"""
        self.stocks = {}  # {股票ID: 股票對象}
        self.order_book = {
            'buy': [],  # [(價格, 數量, 用戶ID, 訂單ID)]
            'sell': []  # [(價格, 數量, 用戶ID, 訂單ID)]
        }
        self.transaction_fee_rate = 0.005  # 交易費率，例如0.5%
        self.central_bank = central_bank
        self.admin_fee_account = None  # 將在系統初始化時設置
        self._users_ref = None  # 將在系統初始化時設置
    
    def set_admin_fee_account(self, admin_user: User):
        """設置管理員費用賬戶"""
        self.admin_fee_account = admin_user
        
    def set_users_ref(self, users_list: List[User]):
        """設置用戶列表引用"""
        self._users_ref = users_list
        
    def _get_all_users(self) -> List[User]:
        """獲取所有用戶列表"""
        return self._users_ref if self._users_ref is not None else []
    
    def add_stock(self, stock: Stock):
        """添加新股票到市場"""
        self.stocks[stock.id] = stock
        print(f"新股票 {stock.name} 已添加到市場，初始價格：{stock.price}，總股數：{stock.total_shares}")
    
    def initial_distribution(self, admin_user: User, stock_id: str, shares: int):
        """初始分配股票給管理員"""
        if stock_id not in self.stocks:
            print(f"錯誤：找不到股票ID {stock_id}")
            return False
        
        stock = self.stocks[stock_id]
        
        if shares > stock.available_shares:
            print(f"錯誤：可用股數不足。請求：{shares}，可用：{stock.available_shares}")
            return False
        
        # 分配股票給管理員
        if stock_id not in admin_user.stocks:
            admin_user.stocks[stock_id] = 0
        
        admin_user.stocks[stock_id] += shares
        stock.available_shares -= shares
        
        print(f"初始分配：{admin_user.name} 獲得 {shares} 股 {stock.name}")
        return True
    
    def place_buy_order(self, user: User, stock_id: str, price: float, quantity: int) -> Optional[str]:
        """下買單"""
        if stock_id not in self.stocks:
            print(f"錯誤：找不到股票ID {stock_id}")
            return None
        
        total_cost = price * quantity
        transaction_fee = total_cost * self.transaction_fee_rate
        total_payment = total_cost + transaction_fee
        
        if user.balance < total_payment:
            print(f"錯誤：餘額不足。需要：{total_payment}，擁有：{user.balance}")
            return None
        
        # 鎖定資金
        user.balance -= total_payment
        
        # 處理交易費
        if self.admin_fee_account:
            self.admin_fee_account.balance += transaction_fee
            self.central_bank.log_transaction(
                user.name, 
                self.admin_fee_account.name, 
                transaction_fee, 
                'stock_fee'
            )
        
        # 創建訂單
        order_id = str(uuid.uuid4())
        self.order_book['buy'].append((price, quantity, user.id, order_id))
        # 按價格降序排序買單
        self.order_book['buy'].sort(reverse=True)
        
        print(f"{user.name} 下單購買 {quantity} 股 {self.stocks[stock_id].name}，價格：{price}")
        
        # 嘗試撮合訂單
        self._match_orders()
        
        return order_id
    
    def place_sell_order(self, user: User, stock_id: str, price: float, quantity: int) -> Optional[str]:
        """下賣單"""
        if stock_id not in self.stocks:
            print(f"錯誤：找不到股票ID {stock_id}")
            return None
        
        if stock_id not in user.stocks or user.stocks[stock_id] < quantity:
            print(f"錯誤：持有股數不足。需要：{quantity}，擁有：{user.stocks.get(stock_id, 0)}")
            return None
        
        # 鎖定股票
        user.stocks[stock_id] -= quantity
        
        # 創建訂單
        order_id = str(uuid.uuid4())
        self.order_book['sell'].append((price, quantity, user.id, order_id))
        # 按價格升序排序賣單
        self.order_book['sell'].sort()
        
        print(f"{user.name} 下單出售 {quantity} 股 {self.stocks[stock_id].name}，價格：{price}")
        
        # 嘗試撮合訂單
        self._match_orders()
        
        return order_id
    
    def _match_orders(self):
        """撮合訂單"""
        # 確保有買單和賣單
        if not self.order_book['buy'] or not self.order_book['sell']:
            return
        
        # 獲取最高買價和最低賣價
        best_buy = self.order_book['buy'][0]
        best_sell = self.order_book['sell'][0]
        
        # 如果最高買價 >= 最低賣價，可以撮合
        if best_buy[0] >= best_sell[0]:
            buy_price, buy_quantity, buyer_id, buy_order_id = best_buy
            sell_price, sell_quantity, seller_id, sell_order_id = best_sell
            
            # 確定交易價格和數量
            trade_price = (buy_price + sell_price) / 2  # 取買賣價的平均值
            trade_quantity = min(buy_quantity, sell_quantity)
            
            # 找到買家和賣家
            buyer = None
            seller = None
            for user in self._get_all_users():
                if user.id == buyer_id:
                    buyer = user
                elif user.id == seller_id:
                    seller = user
            
            if not buyer or not seller:
                print("錯誤：找不到交易參與者")
                return
            
            # 執行交易
            total_amount = trade_price * trade_quantity
            transaction_fee = total_amount * self.transaction_fee_rate
            
            # 買家已鎖定資金，解鎖未用部分，添加股票
            refund = (buy_price - trade_price) * trade_quantity
            buyer.balance += refund
            
            if stock_id not in buyer.stocks:
                buyer.stocks[stock_id] = 0
            buyer.stocks[stock_id] += trade_quantity
            
            # 賣家接收資金
            seller.balance += (total_amount - transaction_fee)
            
            # 交易費給管理員
            if self.admin_fee_account:
                self.admin_fee_account.balance += transaction_fee
                
            # 更新股票價格
            stock_id = ""  # 需要從訂單中獲取股票ID
            self.stocks[stock_id].update_price(trade_price)
            
            # 記錄交易
            self.central_bank.log_transaction(
                buyer.name, 
                seller.name, 
                total_amount, 
                'stock_trade'
            )
            
            # 更新訂單簿
            self._update_order_book_after_trade(trade_quantity)
            
            print(f"股票交易完成：{buyer.name} 購買 {trade_quantity} 股，價格：{trade_price}，從 {seller.name}")
    
    def _update_order_book_after_trade(self, traded_quantity):
        """交易後更新訂單簿"""
        # 這裡應該實現訂單簿的更新邏輯
        pass
    
    def get_stock_price(self, stock_id: str) -> float:
        """獲取股票當前價格"""
        if stock_id in self.stocks:
            return self.stocks[stock_id].price
        return 0
    
    def get_total_money(self) -> float:
        """獲取股票市場中的總資金（鎖定的買單資金）"""
        total = 0
        for price, quantity, user_id, order_id in self.order_book['buy']:
            total += price * quantity
        return total


class HorseRace:
    """賽馬比賽"""
    
    def __init__(self, race_id: str, horses: List[str], odds: List[float]):
        """初始化賽馬比賽"""
        self.race_id = race_id
        self.horses = horses
        self.odds = odds  # 賠率
        self.bets = {}  # {用戶ID: [(馬匹索引, 金額)]}
        self.winner = None  # 獲勝馬匹的索引
        self.status = "pending"  # pending, active, completed
        self.house_edge = 0.05  # 場地費比例，5%
        self._users_ref = None  # 將在系統初始化時設置
    
    def set_users_ref(self, users_list: List[User]):
        """設置用戶列表引用"""
        self._users_ref = users_list
        
    def _get_all_users(self) -> List[User]:
        """獲取所有用戶列表"""
        return self._users_ref if self._users_ref is not None else []
    
    def place_bet(self, user: User, horse_index: int, amount: float, central_bank: CentralBank) -> bool:
        """下注"""
        if self.status != "pending":
            print("錯誤：比賽已經開始或結束，無法下注")
            return False
        
        if horse_index < 0 or horse_index >= len(self.horses):
            print(f"錯誤：無效的馬匹索引 {horse_index}")
            return False
        
        if amount <= 0:
            print("錯誤：下注金額必須為正數")
            return False
        
        if user.balance < amount:
            print(f"錯誤：餘額不足。需要：{amount}，擁有：{user.balance}")
            return False
        
        # 扣除用戶餘額
        user.balance -= amount
        
        # 記錄下注
        if user.id not in self.bets:
            self.bets[user.id] = []
        
        self.bets[user.id].append((horse_index, amount))
        
        # 記錄交易
        central_bank.log_transaction(
            user.name, 
            f"HorseRace:{self.race_id}", 
            amount, 
            'bet'
        )
        
        print(f"{user.name} 在 {self.horses[horse_index]} 上下注 {amount}")
        return True
    
    def start_race(self):
        """開始比賽"""
        if self.status != "pending":
            print("錯誤：比賽已經開始或結束")
            return
        
        self.status = "active"
        print(f"賽馬比賽 {self.race_id} 開始！")
    
    def end_race(self, admin_user: User, central_bank: CentralBank):
        """結束比賽，決定獲勝者並分發獎金"""
        if self.status != "active":
            print("錯誤：比賽尚未開始或已經結束")
            return
        
        # 隨機決定獲勝馬匹
        self.winner = random.randint(0, len(self.horses) - 1)
        self.status = "completed"
        
        print(f"賽馬比賽 {self.race_id} 結束！獲勝者：{self.horses[self.winner]}")
        
        # 計算總下注額和獲勝下注額
        total_bet_amount = 0
        winning_bet_amount = 0
        
        for user_id, user_bets in self.bets.items():
            for horse_index, amount in user_bets:
                total_bet_amount += amount
                if horse_index == self.winner:
                    winning_bet_amount += amount
        
        # 計算場地費
        house_edge_amount = total_bet_amount * self.house_edge
        
        # 場地費給管理員
        admin_user.balance += house_edge_amount
        central_bank.log_transaction(
            f"HorseRace:{self.race_id}", 
            admin_user.name, 
            house_edge_amount, 
            'house_edge'
        )
        
        # 分發獎金給贏家
        prize_pool = total_bet_amount - house_edge_amount
        
        if winning_bet_amount > 0:
            # 按比例分配獎金
            for user_id, user_bets in self.bets.items():
                user_winning_amount = 0
                
                for horse_index, amount in user_bets:
                    if horse_index == self.winner:
                        # 計算用戶應得獎金比例
                        win_ratio = amount / winning_bet_amount
                        win_amount = prize_pool * win_ratio
                        user_winning_amount += win_amount
                
                if user_winning_amount > 0:
                    user = None
                    for u in self._get_all_users():
                        if u.id == user_id:
                            user = u
                            break
                    if user:
                        user.balance += user_winning_amount
                        central_bank.log_transaction(
                            f"HorseRace:{self.race_id}", 
                            user.name, 
                            user_winning_amount, 
                            'prize'
                        )
                        print(f"{user.name} 贏得 {user_winning_amount} 獎金")
        else:
            # 如果沒有人押中獲勝馬匹，所有獎金給管理員
            admin_user.balance += prize_pool
            central_bank.log_transaction(
                f"HorseRace:{self.race_id}", 
                admin_user.name, 
                prize_pool, 
                'unclaimed_prize'
            )
            print(f"沒有玩家押中獲勝馬匹，所有獎金 {prize_pool} 歸管理員所有")
    
    def get_total_money(self) -> float:
        """獲取賽馬比賽中的總資金（所有下注金額）"""
        total = 0
        for user_bets in self.bets.values():
            for _, amount in user_bets:
                total += amount
        return total


class Casino:
    """賭場類，包含各種賭博遊戲"""
    
    def __init__(self, admin_user: User, central_bank: CentralBank):
        """初始化賭場"""
        self.admin_user = admin_user
        self.central_bank = central_bank
        self.house_edge = 0.05  # 賭場優勢，5%
        self.games = ["roulette", "blackjack", "slot_machine"]
    
    def play_roulette(self, user: User, bet_type: str, bet_amount: float) -> float:
        """玩輪盤賭"""
        if bet_amount <= 0:
            print("錯誤：下注金額必須為正數")
            return 0
        
        if user.balance < bet_amount:
            print(f"錯誤：餘額不足。需要：{bet_amount}，擁有：{user.balance}")
            return 0
        
        # 扣除用戶餘額
        user.balance -= bet_amount
        
        # 記錄交易
        self.central_bank.log_transaction(
            user.name, 
            "Casino:Roulette", 
            bet_amount, 
            'casino_bet'
        )
        
        # 模擬輪盤結果
        roulette_result = random.randint(0, 36)
        
        # 計算獲勝金額
        winnings = 0
        
        if bet_type == "red" and roulette_result in [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]:
            winnings = bet_amount * 2 * (1 - self.house_edge)
        elif bet_type == "black" and roulette_result in [2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35]:
            winnings = bet_amount * 2 * (1 - self.house_edge)
        elif bet_type == "green" and roulette_result == 0:
            winnings = bet_amount * 36 * (1 - self.house_edge)
        
        # 如果贏了，給用戶獎金
        if winnings > 0:
            user.balance += winnings
            self.central_bank.log_transaction(
                "Casino:Roulette", 
                user.name, 
                winnings, 
                'casino_win'
            )
            print(f"{user.name} 在輪盤賭贏得 {winnings}")
        else:
            # 賭場收入
            self.admin_user.balance += bet_amount
            self.central_bank.log_transaction(
                "Casino:Roulette", 
                self.admin_user.name, 
                bet_amount, 
                'casino_profit'
            )
            print(f"{user.name} 在輪盤賭輸掉 {bet_amount}")
        
        return winnings
    
    def play_blackjack(self, user: User, bet_amount: float) -> float:
        """玩二十一點"""
        # 簡化實現，實際應該有完整的遊戲邏輯
        if bet_amount <= 0:
            print("錯誤：下注金額必須為正數")
            return 0
        
        if user.balance < bet_amount:
            print(f"錯誤：餘額不足。需要：{bet_amount}，擁有：{user.balance}")
            return 0
        
        # 扣除用戶餘額
        user.balance -= bet_amount
        
        # 記錄交易
        self.central_bank.log_transaction(
            user.name, 
            "Casino:Blackjack", 
            bet_amount, 
            'casino_bet'
        )
        
        # 模擬遊戲結果，玩家獲勝機率45%
        player_won = random.random() < 0.45
        
        # 計算獲勝金額
        winnings = 0
        
        if player_won:
            winnings = bet_amount * 2 * (1 - self.house_edge)
            user.balance += winnings
            self.central_bank.log_transaction(
                "Casino:Blackjack", 
                user.name, 
                winnings, 
                'casino_win'
            )
            print(f"{user.name} 在二十一點贏得 {winnings}")
        else:
            # 賭場收入
            self.admin_user.balance += bet_amount
            self.central_bank.log_transaction(
                "Casino:Blackjack", 
                self.admin_user.name, 
                bet_amount, 
                'casino_profit'
            )
            print(f"{user.name} 在二十一點輸掉 {bet_amount}")
        
        return winnings
    
    def play_slot_machine(self, user: User, bet_amount: float) -> float:
        """玩老虎機"""
        if bet_amount <= 0:
            print("錯誤：下注金額必須為正數")
            return 0
        
        if user.balance < bet_amount:
            print(f"錯誤：餘額不足。需要：{bet_amount}，擁有：{user.balance}")
            return 0
        
        # 扣除用戶餘額
        user.balance -= bet_amount
        
        # 記錄交易
        self.central_bank.log_transaction(
            user.name, 
            "Casino:SlotMachine", 
            bet_amount, 
            'casino_bet'
        )
        
        # 模擬老虎機結果，中獎機率10%
        jackpot = random.random() < 0.1
        
        # 計算獲勝金額
        winnings = 0
        
        if jackpot:
            winnings = bet_amount * 8 * (1 - self.house_edge)  # 8倍賠率
            user.balance += winnings
            self.central_bank.log_transaction(
                "Casino:SlotMachine", 
                user.name, 
                winnings, 
                'casino_win'
            )
            print(f"{user.name} 在老虎機贏得 {winnings}")
        else:
            # 賭場收入
            self.admin_user.balance += bet_amount
            self.central_bank.log_transaction(
                "Casino:SlotMachine", 
                self.admin_user.name, 
                bet_amount, 
                'casino_profit'
            )
            print(f"{user.name} 在老虎機輸掉 {bet_amount}")
        
        return winnings
    
    def get_total_money(self) -> float:
        """賭場中沒有鎖定的資金，始終返回0"""
        return 0


class GamblingSystem:
    """賭博系統類，管理所有賭博活動"""
    
    def __init__(self, admin_user: User, central_bank: CentralBank):
        """初始化賭博系統"""
        self.admin_user = admin_user
        self.central_bank = central_bank
        self.horse_races = {}  # {比賽ID: 比賽對象}
        self.casino = Casino(admin_user, central_bank)
    
    def create_horse_race(self, race_id: str, horses: List[str], odds: List[float], users_list: List[User]) -> HorseRace:
        """創建新賽馬比賽"""
        if race_id in self.horse_races:
            print(f"錯誤：比賽ID {race_id} 已存在")
            return None
        
        race = HorseRace(race_id, horses, odds)
        race.set_users_ref(users_list)  # 設置用戶列表引用
        self.horse_races[race_id] = race
        
        print(f"新賽馬比賽 {race_id} 已創建，參賽馬匹：{', '.join(horses)}")
        return race
    
    def get_total_money(self) -> float:
        """獲取賭博系統中的總資金"""
        total = 0
        
        # 所有賽馬比賽中的資金
        for race in self.horse_races.values():
            total += race.get_total_money()
        
        # 賭場中的資金（理論上應為0）
        total += self.casino.get_total_money()
        
        return total


class EconomicSystem:
    """經濟系統類，整合所有組件"""
    
    def __init__(self, total_money: float):
        """初始化經濟系統"""
        self.central_bank = CentralBank(total_money)
        self.users = []
        self.admin_user = None
        self.stock_market = StockMarket(self.central_bank)
        self.gambling_system = None  # 稍後初始化
    
    def create_admin(self, name: str, initial_balance: float):
        """創建管理員用戶"""
        admin = User(name, is_admin=True, initial_balance=initial_balance)
        self.users.append(admin)
        self.admin_user = admin
        
        # 設置股票市場的管理員賬戶和用戶列表引用
        self.stock_market.set_admin_fee_account(admin)
        self.stock_market.set_users_ref(self.users)
        
        # 初始化賭博系統
        self.gambling_system = GamblingSystem(admin, self.central_bank)
        
        print(f"管理員 {name} 已創建，初始餘額：{initial_balance}")
        return admin
    
    def create_user(self, name: str, initial_balance: float = 0):
        """創建普通用戶"""
        user = User(name, is_admin=False, initial_balance=initial_balance)
        self.users.append(user)
        
        print(f"用戶 {name} 已創建，初始餘額：{initial_balance}")
        return user
    
    def find_user_by_id(self, user_id: str) -> Optional[User]:
        """通過ID查找用戶"""
        for user in self.users:
            if user.id == user_id:
                return user
        return None
    
    def audit_system(self):
        """審計系統，確保總貨幣量不變"""
        return self.central_bank.audit(self.users, self.stock_market, self.gambling_system)
    
    def initialize_stock_market(self, stocks_info: List[Tuple[str, float, int]]):
        """初始化股票市場"""
        for name, initial_price, total_shares in stocks_info:
            stock = Stock(name, initial_price, total_shares)
            self.stock_market.add_stock(stock)
            
            # 分配大部分股票給管理員（例如80%）
            admin_shares = int(total_shares * 0.8)
            self.stock_market.initial_distribution(self.admin_user, stock.id, admin_shares)
    
    def simulate_day(self):
        """模擬一天的經濟活動"""
        print("\n=== 模擬一天的經濟活動 ===")
        
        # 支付股息
        for stock in self.stock_market.stocks.values():
            stock.pay_dividend(self.users, self.central_bank)
        
        # 創建賽馬比賽
        race_id = f"race_{len(self.gambling_system.horse_races) + 1}"
        horses = ["閃電", "風暴", "黑旋風", "勝利者", "冠軍"]
        odds = [2.5, 3.0, 4.0, 3.5, 5.0]
        race = self.gambling_system.create_horse_race(race_id, horses, odds, self.users)
        
        # 用戶下注
        for user in self.users:
            if not user.is_admin and user.balance > 0:
                # 隨機下注
                horse_index = random.randint(0, len(horses) - 1)
                bet_amount = min(user.balance * 0.1, 100)  # 最多下注10%的餘額或100
                race.place_bet(user, horse_index, bet_amount, self.central_bank)
        
        # 開始和結束比賽
        race.start_race()
        race.end_race(self.admin_user, self.central_bank)
        
        # 用戶玩賭場遊戲
        for user in self.users:
            if not user.is_admin and user.balance > 0:
                # 隨機選擇遊戲
                game = random.choice(self.gambling_system.casino.games)
                bet_amount = min(user.balance * 0.05, 50)  # 最多下注5%的餘額或50
                
                if game == "roulette":
                    bet_type = random.choice(["red", "black", "green"])
                    self.gambling_system.casino.play_roulette(user, bet_type, bet_amount)
                elif game == "blackjack":
                    self.gambling_system.casino.play_blackjack(user, bet_amount)
                elif game == "slot_machine":
                    self.gambling_system.casino.play_slot_machine(user, bet_amount)
        
        # 用戶交易股票
        for stock_id, stock in self.stock_market.stocks.items():
            for user in self.users:
                if not user.is_admin and user.balance > 0:
                    # 50%機率買入，50%機率賣出
                    if random.random() < 0.5 and user.balance > stock.price:
                        # 買入
                        quantity = random.randint(1, max(1, int(user.balance / stock.price / 2)))
                        price = stock.price * (0.95 + random.random() * 0.1)  # 價格波動±5%
                        self.stock_market.place_buy_order(user, stock_id, price, quantity)
                    elif stock_id in user.stocks and user.stocks[stock_id] > 0:
                        # 賣出
                        quantity = random.randint(1, user.stocks[stock_id])
                        price = stock.price * (0.95 + random.random() * 0.1)  # 價格波動±5%
                        self.stock_market.place_sell_order(user, stock_id, price, quantity)
        
        # 審計系統
        self.audit_system()
        
        # 打印用戶餘額
        self._print_user_balances()
    
    def _print_user_balances(self):
        """打印所有用戶的餘額"""
        print("\n=== 用戶餘額 ===")
        total_balance = 0
        for user in self.users:
            print(f"{user.name}: {user.balance}")
            total_balance += user.balance
        print(f"總餘額: {total_balance}")


# 示例用法
def main():
    # 創建經濟系統，總貨幣量10,000,000
    system = EconomicSystem(1000000)
    
    # 創建管理員，初始餘額7,000,000（70%的總貨幣量）
    admin = system.create_admin("超級管理員", 7000000)
    
    # 創建一些普通用戶
    user1 = system.create_user("玩家1", 50000)
    user2 = system.create_user("玩家2", 50000)
    user3 = system.create_user("玩家3", 50000)
    user4 = system.create_user("玩家3", 50000)
    user5 = system.create_user("玩家3", 50000)
    user6 = system.create_user("玩家3", 50000)
    
    
    # 初始化股票市場
    stocks_info = [
        ("科技公司", 10000, 10000),  # 名稱，初始價格，總股數
        ("銀行", 8000, 12000),
        ("醫療", 1200, 8000),
        ("能源", 6000, 15000)
    ]
    system.initialize_stock_market(stocks_info)
    
    # 審計系統，確保總貨幣量不變
    system.audit_system()
    
    # 模擬幾天的經濟活動
    for i in range(5):
        print(f"\n\n==== 第 {i+1} 天 ====")
        system.simulate_day()


if __name__ == "__main__":
    main()