import datetime
from utils.database import get_db_connection, execute_query, execute_transaction, table_exists, column_exists

class Currency:
    """Silva幣系統模型"""
    
    def __init__(self, bot):
        self.bot = bot
        self.db_name = "currency"
        
    async def setup_database(self):
        """初始化資料庫表格"""
        conn = await get_db_connection(self.db_name)
        cursor = await conn.cursor()
        
        # 用戶貨幣表格
        await cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_currency (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            balance INTEGER DEFAULT 0,
            last_daily TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 交易歷史表格
        await cursor.execute('''
        CREATE TABLE IF NOT EXISTS transaction_history (
            transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount INTEGER NOT NULL,
            balance_after INTEGER NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES user_currency(user_id)
        )
        ''')
        
        # 檢查是否需要添加欄位
        add_columns = []
        
        if not await column_exists(self.db_name, "user_currency", "updated_at"):
            add_columns.append(
                ("ALTER TABLE user_currency ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP", ())
            )
            
        if not await column_exists(self.db_name, "user_currency", "last_daily"):
            add_columns.append(
                ("ALTER TABLE user_currency ADD COLUMN last_daily TIMESTAMP", ())
            )
            
        if not await column_exists(self.db_name, "user_currency", "username"):
            add_columns.append(
                ("ALTER TABLE user_currency ADD COLUMN username TEXT", ())
            )
        
        # 執行添加欄位操作
        if add_columns:
            await execute_transaction(self.db_name, add_columns)
            
        await conn.commit()

    async def get_balance(self, user_id: int) -> int:
        """查詢用戶餘額"""
        # 確保資料庫已設置
        await self.setup_database()
        
        query = 'SELECT balance FROM user_currency WHERE user_id = ?'
        result = await execute_query(self.db_name, query, (user_id,), 'one')
        
        if result is None:
            # 如果用戶不存在，創建新用戶
            await execute_query(
                self.db_name,
                'INSERT INTO user_currency (user_id, balance) VALUES (?, ?)',
                (user_id, 0)
            )
            return 0
            
        return result[0]

    async def update_balance(self, user_id: int, amount: int, username: str):
        """更新用戶餘額"""
        # 確保資料庫已設置
        await self.setup_database()
        
        try:
            # 開始事務
            queries = []
            
            # 檢查用戶當前餘額
            current_balance = await self.get_balance(user_id)
            new_balance = current_balance + amount
            
            # 確保餘額不會變成負數
            if new_balance < 0:
                return False
            
            # 更新用戶餘額
            queries.append((
                '''
                INSERT INTO user_currency (user_id, balance, username, updated_at) 
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) 
                DO UPDATE SET 
                    balance = ?,
                    username = ?,
                    updated_at = CURRENT_TIMESTAMP
                ''',
                (user_id, int(new_balance), username, int(new_balance), username)
            ))
            
            # 記錄交易歷史
            queries.append((
                '''
                INSERT INTO transaction_history 
                    (user_id, amount, balance_after, description)
                VALUES (?, ?, ?, ?)
                ''',
                (user_id, int(amount), int(new_balance), f"餘額變動: {int(amount):+,} Silva幣")
            ))
            
            success = await execute_transaction(self.db_name, queries)
            return success
            
        except Exception as e:
            print(f"更新餘額時發生錯誤: {e}")
            return False

    async def get_transaction_history(self, user_id: int, limit: int = 10) -> list:
        """獲取用戶的交易歷史"""
        # 確保資料庫已設置
        await self.setup_database()
        
        query = '''
        SELECT amount, balance_after, description, created_at
        FROM transaction_history
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT ?
        '''
        
        result = await execute_query(self.db_name, query, (user_id, limit), 'all')
        return result or []

    async def get_top_balance(self, limit: int = 10) -> list:
        """獲取餘額排行榜"""
        # 確保資料庫已設置
        await self.setup_database()
        
        query = '''
        SELECT username, balance
        FROM user_currency
        WHERE balance > 0
        ORDER BY balance DESC
        LIMIT ?
        '''
        
        result = await execute_query(self.db_name, query, (limit,), 'all')
        return result or []
        
    async def update_daily(self, user_id: int, username: str, amount: int):
        """更新用戶每日獎勵"""
        # 確保資料庫已設置
        await self.setup_database()
        
        now = datetime.datetime.now()
        
        # 檢查上次領取時間
        query = 'SELECT last_daily FROM user_currency WHERE user_id = ?'
        result = await execute_query(self.db_name, query, (user_id,), 'one')
        
        if result and result[0]:
            last_claim = datetime.datetime.strptime(result[0], '%Y-%m-%d %H:%M:%S.%f')
            if (now - last_claim).days < 1:
                time_until_next = (last_claim + datetime.timedelta(days=1)) - now
                return False, time_until_next
        
        # 更新餘額和領取時間
        query = '''
        INSERT INTO user_currency (user_id, balance, last_daily, username) 
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id) 
        DO UPDATE SET balance = balance + ?, last_daily = ?, username = ?
        '''
        
        await execute_query(
            self.db_name, 
            query, 
            (user_id, amount, now, username, amount, now, username)
        )
        
        # 記錄交易歷史
        new_balance = await self.get_balance(user_id)
        
        query = '''
        INSERT INTO transaction_history 
            (user_id, amount, balance_after, description)
        VALUES (?, ?, ?, ?)
        '''
        
        await execute_query(
            self.db_name,
            query,
            (user_id, amount, new_balance, f"每日獎勵: +{amount:,} Silva幣")
        )
        
        return True, new_balance