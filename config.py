import json
import os

# 預設設定
DEFAULT_CONFIG = {
    'Silva': 'MTE4OTE3NTA0MDgyMzAwNTE5NA.GVELNn.XCCchjGQdljTW3CGXmqOCCPmsUlajI5G_pop-Q', 
    'welcome_channel':1310566224006090752,
    'race_channel': 1310818435361407016,
    'level_channel': 1310592500657815645
}

def load_config(file_path='set.json'):
    """
    載入設定檔，如果檔案不存在則創建一個預設設定檔
    
    Args:
        file_path (str): 設定檔路徑
        
    Returns:
        dict: 設定檔內容
    """
    try:
        # 檢查檔案是否存在
        if not os.path.exists(file_path):
            # 如果不存在，創建預設設定檔
            with open(file_path, 'w', encoding='utf8') as f:
                json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=4)
            return DEFAULT_CONFIG
            
        # 讀取設定檔
        with open(file_path, 'r', encoding='utf8') as f:
            config = json.load(f)
            
        # 將預設設定與讀取的設定合併，確保所有設定值都存在
        for key, value in DEFAULT_CONFIG.items():
            if key not in config:
                config[key] = value
                
        return config
    except Exception as e:
        print(f"載入設定檔時發生錯誤: {e}")
        return DEFAULT_CONFIG

def save_config(config, file_path='set.json'):
    """
    儲存設定檔
    
    Args:
        config (dict): 設定檔內容
        file_path (str): 設定檔路徑
        
    Returns:
        bool: 是否成功儲存
    """
    try:
        with open(file_path, 'w', encoding='utf8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"儲存設定檔時發生錯誤: {e}")
        return False

def get_config_value(key, default=None):
    """
    取得設定值
    
    Args:
        key (str): 設定鍵值
        default: 預設值，如果設定不存在則返回此值
        
    Returns:
        設定值或預設值
    """
    config = load_config()
    return config.get(key, default)

def set_config_value(key, value):
    """
    設定設定值並儲存
    
    Args:
        key (str): 設定鍵值
        value: 設定值
        
    Returns:
        bool: 是否成功設定
    """
    config = load_config()
    config[key] = value
    return save_config(config)