# import discord
# from discord.ext import commands, tasks
# from discord import app_commands
# import random
# import asyncio
# import datetime
# import sys
# import os

# # 獲取主目錄絕對路徑
# current_dir = os.path.dirname(os.path.abspath(__file__))
# parent_dir = os.path.dirname(current_dir)

# # 添加到路徑
# if parent_dir not in sys.path:
#     sys.path.insert(0, parent_dir)

# # 現在使用絕對導入
# from utils.database import execute_query, get_db_connection

# class MarketNewsSystem:
#     """市場新聞系統模型"""
    
#     def __init__(self, bot):
#         self.bot = bot
#         self.db_name = "stocks"
#         self.news_channel_id = None
        
#     async def setup_database(self):
#         """初始化新聞資料庫表格"""
#         conn = await get_db_connection(self.db_name)
#         cursor = await conn.cursor()
        
#         # 新聞表格
#         await cursor.execute('''
#         CREATE TABLE IF NOT EXISTS market_news (
#             news_id INTEGER PRIMARY KEY AUTOINCREMENT,
#             news_title TEXT,
#             news_content TEXT,
#             affected_ticker TEXT,
#             impact_percent REAL,
#             published_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#         )
#         ''')
        
#         # 新聞頻道表格
#         await cursor.execute('''
#         CREATE TABLE IF NOT EXISTS settings (
#             key TEXT PRIMARY KEY,
#             value TEXT
#         )
#         ''')
        
#         await conn.commit()
        
#     async def get_news_channel(self):
#         """獲取新聞頻道ID"""
#         if self.news_channel_id:
#             return self.news_channel_id
            
#         query = "SELECT value FROM settings WHERE key = 'news_channel_id'"
#         result = await execute_query(self.db_name, query, fetch_type='one')
        
#         if result:
#             self.news_channel_id = int(result[0])
            
#         return self.news_channel_id
        
#     async def set_news_channel(self, channel_id):
#         """設置新聞頻道ID"""
#         await self.setup_database()
        
#         query = '''
#         INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)
#         '''
        
#         await execute_query(self.db_name, query, ('news_channel_id', str(channel_id)))
#         self.news_channel_id = channel_id
        
#     async def generate_market_news(self):
#         """生成市場新聞"""
#         await self.setup_database()
        
#         # 獲取所有股票
#         query = 'SELECT ticker, name, category, current_price FROM stocks'
#         stocks = await execute_query(self.db_name, query, fetch_type='all')
        
#         if not stocks or len(stocks) == 0:
#             return None
            
#         # 隨機選擇一支股票
#         ticker, name, category, current_price = random.choice(stocks)
        
#         # 決定是好消息還是壞消息
#         is_good_news = random.random() < 0.6  # 60%概率是好消息
        
#         # 生成影響幅度 (好消息: 2-15%, 壞消息: -2% 到 -12%)
#         if is_good_news:
#             impact_percent = random.uniform(2.0, 15.0)
#         else:
#             impact_percent = random.uniform(-12.0, -2.0)
            
#         # 根據股票類型生成新聞
#         news_data = self.create_news_content(ticker, name, category, is_good_news, impact_percent)
        
#         # 應用價格變化
#         await self.apply_news_impact(ticker, impact_percent)
        
#         # 保存新聞到資料庫
#         query = '''
#         INSERT INTO market_news 
#             (news_title, news_content, affected_ticker, impact_percent) 
#         VALUES (?, ?, ?, ?)
#         '''
        
#         await execute_query(
#             self.db_name, 
#             query, 
#             (news_data['title'], news_data['content'], ticker, impact_percent)
#         )
        
#         return news_data
    
#     def create_news_content(self, ticker, name, category, is_good_news, impact_percent):
#         """創建新聞內容"""
#         titles = []
#         contents = []
        
#         if category == 'horse':  # 賽馬股票
#             if is_good_news:
#                 titles = [
#                     f"{name}宣布擴建賽馬場！",
#                     f"頂級騎師加入{name}團隊！",
#                     f"{name}獲得國際賽事主辦權！",
#                     f"名駒「閃電飛馳」加入{name}賽事！",
#                     f"{name}推出全新賽事獎金制度！",
#                     f"投資者看好{name}未來發展！",
#                     f"{name}與知名品牌達成贊助協議！"
#                 ]
#                 contents = [
#                     f"{name}宣布將投資500萬擴建現有賽馬場，增加觀眾席位和改善設施，預期未來收入將大幅增加。",
#                     f"國際頂級騎師剛剛簽約加入{name}，預計將吸引更多高水平賽事和觀眾。",
#                     f"{name}成功申辦下屆國際大賽，這將為公司帶來可觀的收入和品牌價值提升。",
#                     f"價值連城的冠軍賽駒「閃電飛馳」已被{name}收購，將參加未來賽事，預計大幅提升觀眾人數。",
#                     f"{name}推出全新獎金制度，大幅提高獎金總額，吸引更多頂級賽馬參賽。",
#                     f"多家投資機構發布報告，一致看好{name}的未來發展前景，建議投資者增持該股。",
#                     f"{name}與知名運動品牌達成三年贊助協議，合約總價值超過預期。"
#                 ]
#             else:
#                 titles = [
#                     f"{name}主要賽事被取消！",
#                     f"{name}場地遭檢查發現問題！",
#                     f"頂級騎師離開{name}！",
#                     f"{name}營收未達預期！",
#                     f"{name}遭遇監管調查！",
#                     f"{name}賽事票房大幅下滑！",
#                     f"{name}面臨競爭對手挑戰！"
#                 ]
#                 contents = [
#                     f"由於安全問題，{name}下個月的主要賽事被迫取消，這將對本季度收入產生負面影響。",
#                     f"最近的例行檢查中，監管機構在{name}場地發現多項安全隱患，要求立即整改並暫停部分賽事。",
#                     f"{name}的王牌騎師宣布轉投競爭對手，可能帶走部分忠實觀眾。",
#                     f"{name}剛剛公布的季度報告顯示，營收和利潤均未達到分析師預期，引發投資者擔憂。",
#                     f"有消息稱{name}正面臨監管機構的調查，具體原因尚未公開，但已引起市場擔憂。",
#                     f"{name}最近幾場賽事票房收入大幅下滑，同比下降超過30%。",
#                     f"新開業的競爭對手推出多項優惠政策，已吸引部分{name}的常客轉移。"
#                 ]
#         else:  # 賭場股票
#             if is_good_news:
#                 titles = [
#                     f"{name}推出全新遊戲大獲成功！",
#                     f"{name}季度盈利超出預期！",
#                     f"{name}獲得新區域營運許可！",
#                     f"{name}將進行重大擴建！",
#                     f"知名投資者大舉增持{name}股票！",
#                     f"{name}與國際酒店集團達成合作！",
#                     f"{name}推出會員優惠計劃反響熱烈！"
#                 ]
#                 contents = [
#                     f"{name}推出的全新遊戲大受歡迎，上線首週已創造超過預期50%的收益。",
#                     f"{name}剛發布的季度財報顯示，盈利超出市場預期20%，主要得益於VIP客戶消費增加。",
#                     f"{name}成功獲得新區域的營運許可證，這將使其業務範圍顯著擴大，預計帶來可觀收入。",
#                     f"{name}宣布斥資2億進行重大擴建計劃，完成後將增加30%的營業面積和全新的高端設施。",
#                     f"知名投資大亨公開表示看好{name}前景，已大舉增持其股票，成為第二大股東。",
#                     f"{name}與國際知名酒店集團達成合作協議，將提供更優質的配套服務和跨品牌會員福利。",
#                     f"{name}新推出的會員優惠計劃反響熱烈，一週內新增會員數超過1萬人。"
#                 ]
#             else:
#                 titles = [
#                     f"{name}營收意外下滑！",
#                     f"{name}面臨新稅費政策衝擊！",
#                     f"{name}高管突然離職！",
#                     f"{name}VIP客戶數量減少！",
#                     f"競爭對手在{name}附近開設新場所！",
#                     f"{name}設備老化需大筆維護資金！",
#                     f"{name}國際客戶減少，收入受影響！"
#                 ]
#                 contents = [
#                     f"{name}最近一個月營收出現意外下滑，比去年同期減少15%，管理層正在調查原因。",
#                     f"當地政府宣布對賭場行業增加新稅費，分析師預計這將影響{name}20%的利潤。",
#                     f"{name}的首席運營官突然宣布離職，市場對管理層穩定性產生擔憂。",
#                     f"{name}的財務報告顯示，高端VIP客戶數量比上季度減少25%，對利潤產生顯著影響。",
#                     f"一家國際知名賭場集團宣布將在{name}附近開設新場所，預計將帶來激烈競爭。",
#                     f"{name}部分設備已使用多年，需要投入大筆資金進行更新，這可能影響短期利潤。",
#                     f"由於國際旅行限制，{name}的國際客戶數量大幅減少，嚴重影響高端收入。"
#                 ]
            
#         # 隨機選擇標題和內容
#         title = random.choice(titles)
#         content = random.choice(contents)
        
#         # 添加股價預測
#         if is_good_news:
#             impact_text = f"分析師預計這一消息將推動 {ticker} 股價上漲約 {abs(impact_percent):.2f}%。"
#         else:
#             impact_text = f"分析師預計這一消息將導致 {ticker} 股價下跌約 {abs(impact_percent):.2f}%。"
            
#         full_content = f"{content}\n\n{impact_text}"
        
#         return {
#             'title': title,
#             'content': full_content,
#             'ticker': ticker,
#             'impact': impact_percent
#         }
    
#     async def apply_news_impact(self, ticker, impact_percent):
#         """應用新聞對股價的影響"""
#         # 獲取當前股價
#         query = 'SELECT stock_id, current_price FROM stocks WHERE ticker = ?'
#         stock_info = await execute_query(self.db_name, query, (ticker,), 'one')
        
#         if not stock_info:
#             return False
            
#         stock_id, current_price = stock_info
        
#         # 計算新價格
#         new_price = current_price * (1 + impact_percent / 100)
        
#         # 更新股價
#         query = '''
#         UPDATE stocks 
#         SET current_price = ?, updated_at = CURRENT_TIMESTAMP 
#         WHERE stock_id = ?
#         '''
        
#         await execute_query(self.db_name, query, (new_price, stock_id))
        
#         # 記錄價格歷史
#         query = 'INSERT INTO price_history (stock_id, price) VALUES (?, ?)'
#         await execute_query(self.db_name, query, (stock_id, new_price))
        
#         return True
        
#     async def get_recent_news(self, limit=5):
#         """獲取最近新聞"""
#         query = '''
#         SELECT news_title, news_content, affected_ticker, impact_percent, published_at
#         FROM market_news
#         ORDER BY published_at DESC
#         LIMIT ?
#         '''
        
#         news = await execute_query(self.db_name, query, (limit,), 'all')
#         return news


# class NewsCog(commands.Cog):
#     """股市新聞系統"""

#     def __init__(self, bot):
#         self.bot = bot
#         self.news_system = MarketNewsSystem(bot)
#         self.news_task = None
#         self.start_news_system()
        
#     def cog_unload(self):
#         """Cog 卸載時停止任務"""
#         self.stop_news_system()
        
#     def start_news_system(self):
#         """啟動新聞系統"""
#         if self.news_task is None or self.news_task.done():
#             self.news_task = self.bot.loop.create_task(self.news_loop())
#             print("股市新聞系統已啟動")
        
#     def stop_news_system(self):
#         """停止新聞系統"""
#         if self.news_task and not self.news_task.done():
#             self.news_task.cancel()
#             print("股市新聞系統已停止")
        
#     async def news_loop(self):
#         """新聞發布循環"""
#         await self.bot.wait_until_ready()
        
#         while not self.bot.is_closed():
#             try:
#                 # 獲取新聞頻道
#                 channel_id = await self.news_system.get_news_channel()
                
#                 if not channel_id:
#                     # 如果沒有設置頻道，等待一段時間後重試
#                     await asyncio.sleep(300)  # 5分鐘
#                     continue
                    
#                 channel = self.bot.get_channel(channel_id)
                
#                 if not channel:
#                     await asyncio.sleep(300)  # 5分鐘
#                     continue
                
#                 # 生成新聞
#                 news_data = await self.news_system.generate_market_news()
                
#                 if news_data:
#                     # 創建新聞嵌入
#                     embed = discord.Embed(
#                         title=f"📰 股市快訊: {news_data['title']}",
#                         description=news_data['content'],
#                         color=discord.Color.gold() if news_data['impact'] > 0 else discord.Color.red(),
#                         timestamp=datetime.datetime.now()
#                     )
                    
#                     # 添加影響信息
#                     impact_emoji = "📈" if news_data['impact'] > 0 else "📉"
#                     embed.add_field(
#                         name="影響股票", 
#                         value=f"{impact_emoji} {news_data['ticker']} ({'+' if news_data['impact'] > 0 else ''}{news_data['impact']:.2f}%)",
#                         inline=False
#                     )
                    
#                     embed.set_footer(text="SilvaStock 股市快訊")
                    
#                     await channel.send(embed=embed)
                
#                 # 隨機等待5-10分鐘
#                 wait_time = random.randint(300, 3600)  # 5-10分鐘
#                 await asyncio.sleep(wait_time)
                
#             except asyncio.CancelledError:
#                 # 任務被取消
#                 break
#             except Exception as e:
#                 print(f"新聞系統發生錯誤: {e}")
#                 await asyncio.sleep(300)  # 發生錯誤後等待5分鐘再嘗試
    
#     @app_commands.command(name="setnewschannel", description="設置股市新聞頻道 (管理員專用)")
#     @app_commands.default_permissions(administrator=True)
#     async def set_news_channel(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
#         """設置股市新聞頻道"""
#         if not interaction.user.guild_permissions.administrator:
#             await interaction.response.send_message("你沒有權限使用此指令!", ephemeral=True)
#             return
            
#         # 如果沒有提供頻道，使用當前頻道
#         target_channel = channel or interaction.channel
        
#         # 更新設置
#         await self.news_system.set_news_channel(target_channel.id)
        
#         # 確保新聞系統正在運行
#         self.start_news_system()
        
#         await interaction.response.send_message(
#             f"✅ 已將股市新聞頻道設定為 {target_channel.mention}",
#             ephemeral=False
#         )
    
#     @app_commands.command(name="recentnews", description="查看最近的股市新聞")
#     async def recent_news(self, interaction: discord.Interaction, count: int = 3):
#         """查看最近的股市新聞"""
#         if count < 1:
#             count = 1
#         elif count > 10:
#             count = 10
            
#         news = await self.news_system.get_recent_news(count)
        
#         if not news:
#             await interaction.response.send_message("目前沒有任何股市新聞！", ephemeral=True)
#             return
            
#         embed = discord.Embed(
#             title="📰 最近股市新聞",
#             description=f"顯示最近 {len(news)} 條新聞",
#             color=discord.Color.blue()
#         )
        
#         for i, (title, content, ticker, impact, date) in enumerate(news):
#             # 處理日期格式
#             if isinstance(date, str):
#                 try:
#                     date = datetime.datetime.strptime(date, '%Y-%m-%d %H:%M:%S.%f')
#                 except ValueError:
#                     try:
#                         date = datetime.datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
#                     except:
#                         date = datetime.datetime.now()
                        
#             impact_emoji = "📈" if impact > 0 else "📉"
#             embed.add_field(
#                 name=f"{i+1}. {title} ({date.strftime('%m/%d %H:%M')})",
#                 value=f"{content}\n{impact_emoji} {ticker}: {'+' if impact > 0 else ''}{impact:.2f}%",
#                 inline=False
#             )
            
#         await interaction.response.send_message(embed=embed)
        
#     @app_commands.command(name="pausenews", description="暫停股市新聞系統 (管理員專用)")
#     @app_commands.default_permissions(administrator=True)
#     async def pause_news(self, interaction: discord.Interaction):
#         """暫停股市新聞系統"""
#         if not interaction.user.guild_permissions.administrator:
#             await interaction.response.send_message("你沒有權限使用此指令!", ephemeral=True)
#             return
            
#         self.stop_news_system()
        
#         await interaction.response.send_message(
#             "✅ 股市新聞系統已暫停",
#             ephemeral=False
#         )
        
#     @app_commands.command(name="resumetnews", description="恢復股市新聞系統 (管理員專用)")
#     @app_commands.default_permissions(administrator=True)
#     async def resume_news(self, interaction: discord.Interaction):
#         """恢復股市新聞系統"""
#         if not interaction.user.guild_permissions.administrator:
#             await interaction.response.send_message("你沒有權限使用此指令!", ephemeral=True)
#             return
            
#         self.start_news_system()
        
#         await interaction.response.send_message(
#             "✅ 股市新聞系統已恢復運行",
#             ephemeral=False
#         )

# async def setup(bot):
#     await bot.add_cog(NewsCog(bot))