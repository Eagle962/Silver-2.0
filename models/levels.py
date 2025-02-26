import math
from utils.database import get_db_connection, execute_query, table_exists

class LevelSystem:
    """等級系統模型"""
    
    def __init__(self, bot):
        self.bot = bot
        self.db_name = "levels"
        
    async def setup_database(self):
        """初始化資料庫表格"""
        conn = await get_db_connection(self.db_name)
        cursor = await conn.cursor()
        
        await cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_levels (
            user_id INTEGER PRIMARY KEY,
            exp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 0,
            message_count INTEGER DEFAULT 0,
            last_message_time TIMESTAMP
        )''')
        
        await conn.commit()
        
    def calculate_exp_for_next_level(self, level):
        """計算升級所需經驗值"""
        # 使用指數增長公式計算下一等級所需經驗
        # 1級需要5經驗，之後每級增加1.5倍
        return int(5 * (math.pow(1.5, level)))
        
    async def add_exp(self, user_id: int, exp_gain=1):
        """增加用戶經驗值"""
        # 確保資料庫已設置
        await self.setup_database()
        
        # 獲取或創建用戶數據
        query = 'INSERT OR IGNORE INTO user_levels (user_id, exp, level, message_count) VALUES (?, 0, 0, 0)'
        await execute_query(self.db_name, query, (user_id,))
        
        # 獲取當前數據
        query = 'SELECT exp, level FROM user_levels WHERE user_id = ?'
        result = await execute_query(self.db_name, query, (user_id,), 'one')
        
        if not result:
            return None
            
        current_exp, current_level = result
        
        # 更新經驗值和訊息計數
        new_exp = current_exp + exp_gain
        query = '''
        UPDATE user_levels 
        SET exp = ?, message_count = message_count + 1, last_message_time = CURRENT_TIMESTAMP
        WHERE user_id = ?
        '''
        
        await execute_query(self.db_name, query, (new_exp, user_id))
        
        # 檢查是否升級
        new_level = current_level
        while new_exp >= self.calculate_exp_for_next_level(new_level):
            new_level += 1
        
        # 如果等級變化，更新數據庫
        if new_level != current_level:
            query = 'UPDATE user_levels SET level = ? WHERE user_id = ?'
            await execute_query(self.db_name, query, (new_level, user_id))
            return new_level
        
        return None
        
    async def get_user_stats(self, user_id: int):
        """獲取用戶等級統計資訊"""
        # 確保資料庫已設置
        await self.setup_database()
        
        query = '''
        SELECT level, exp, message_count 
        FROM user_levels 
        WHERE user_id = ?
        '''
        
        result = await execute_query(self.db_name, query, (user_id,), 'one')
        
        if result:
            level, exp, message_count = result
            next_level_exp = self.calculate_exp_for_next_level(level)
            
            return {
                'level': level,
                'exp': exp,
                'next_level_exp': next_level_exp,
                'message_count': message_count
            }
        
        return None
        
    async def get_leaderboard(self, limit=10):
        """獲取等級排行榜"""
        # 確保資料庫已設置
        await self.setup_database()
        
        query = '''
        SELECT user_id, level, exp, message_count
        FROM user_levels
        ORDER BY level DESC, exp DESC
        LIMIT ?
        '''
        
        result = await execute_query(self.db_name, query, (limit,), 'all')
        return result or []