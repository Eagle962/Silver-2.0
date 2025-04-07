import os
import aiosqlite
import asyncio
import sqlite3
from typing import Optional, Dict

# 全域資料庫連接池
_db_connections: Dict[str, aiosqlite.Connection] = {}

async def get_db_connection(db_name: str) -> aiosqlite.Connection:
    """
    取得資料庫連接，如果連接不存在則創建一個新的連接
    
    Args:
        db_name (str): 資料庫名稱
        
    Returns:
        aiosqlite.Connection: 資料庫連接
    """
    global _db_connections
    
    # 檢查連接是否存在且有效
    need_new_connection = True
    if db_name in _db_connections:
        try:
            # 嘗試執行簡單查詢來檢查連接是否有效
            async with _db_connections[db_name].execute("SELECT 1") as cursor:
                await cursor.fetchone()
            need_new_connection = False
        except Exception:
            # 如果出錯，我們需要一個新連接
            try:
                await _db_connections[db_name].close()
            except:
                pass
            need_new_connection = True
    
    if need_new_connection:
        # 確保資料庫檔案存在的資料夾存在
        os.makedirs('data', exist_ok=True)
        
        # 創建新的連接
        _db_connections[db_name] = await aiosqlite.connect(f'data/{db_name}.db')
        
    return _db_connections[db_name]

async def close_db_connections():
    """關閉所有資料庫連接"""
    global _db_connections
    
    tasks = []
    for db_name, conn in _db_connections.items():
        try:
            tasks.append(conn.close())
        except:
            pass
            
    if tasks:
        await asyncio.gather(*tasks)
    
    _db_connections.clear()

async def execute_query(db_name: str, query: str, parameters: tuple = (), fetch_type: str = None):
    """
    執行 SQL 查詢
    
    Args:
        db_name (str): 資料庫名稱
        query (str): SQL 查詢
        parameters (tuple): 查詢參數
        fetch_type (str): 獲取結果的類型，可以是 'one', 'all', 或 None
        
    Returns:
        查詢結果或 None
    """
    conn = await get_db_connection(db_name)
    
    try:
        async with conn.execute(query, parameters) as cursor:
            if fetch_type == 'one':
                return await cursor.fetchone()
            elif fetch_type == 'all':
                return await cursor.fetchall()
            else:
                await conn.commit()
                # 如果是INSERT查詢，返回最後插入的行ID
                if query.strip().upper().startswith("INSERT"):
                    # 獲取最後插入的ID
                    async with conn.execute("SELECT last_insert_rowid()") as id_cursor:
                        last_id = await id_cursor.fetchone()
                        return last_id[0] if last_id else None
                # 否則返回影響的行數
                return cursor.rowcount
    except Exception as e:
        print(f"執行查詢時發生錯誤: {e}")
        return None

async def execute_transaction(db_name: str, queries: list):
    """
    執行交易
    
    Args:
        db_name (str): 資料庫名稱
        queries (list): 查詢列表，每項是 (query, parameters) 的元組
        
    Returns:
        bool: 是否成功執行
    """
    conn = await get_db_connection(db_name)
    
    try:
        async with conn.cursor() as cursor:
            await conn.execute("BEGIN TRANSACTION")
            
            for query, parameters in queries:
                await cursor.execute(query, parameters)
                
            await conn.commit()
            return True
    except Exception as e:
        await conn.rollback()
        print(f"執行交易時發生錯誤: {e}")
        return False

async def table_exists(db_name: str, table_name: str) -> bool:
    """
    檢查資料表是否存在
    
    Args:
        db_name (str): 資料庫名稱
        table_name (str): 資料表名稱
        
    Returns:
        bool: 資料表是否存在
    """
    query = """
    SELECT name FROM sqlite_master 
    WHERE type='table' AND name=?
    """
    result = await execute_query(db_name, query, (table_name,), 'one')
    return result is not None

async def column_exists(db_name: str, table_name: str, column_name: str) -> bool:
    """
    檢查資料表欄位是否存在
    
    Args:
        db_name (str): 資料庫名稱
        table_name (str): 資料表名稱
        column_name (str): 欄位名稱
        
    Returns:
        bool: 欄位是否存在
    """
    query = f"PRAGMA table_info({table_name})"
    result = await execute_query(db_name, query, fetch_type='all')
    
    if result:
        columns = [row[1] for row in result]
        return column_name in columns
    
    return False