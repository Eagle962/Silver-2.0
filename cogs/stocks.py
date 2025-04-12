from discord.ext import tasks
import random
import discord
from discord.ext import commands
from discord import app_commands
import datetime
import asyncio
from discord.ui import View, Button, Select, Modal, TextInput
from models.stocks import Stock
from models.currency import Currency
from config import get_config_value
from utils.database import get_db_connection, execute_query

class BuyStockModal(Modal):
    """購買股票對話框"""
    def __init__(self, stock_code, stock_name, current_price):
        super().__init__(title=f"購買 {stock_code} 股票")
        self.stock_code = stock_code
        self.stock_name = stock_name
        self.current_price = current_price
        
        self.shares = TextInput(
            label="購買數量",
            placeholder="請輸入要購買的股票數量",
            min_length=1,
            max_length=10,
            required=True
        )
        self.add_item(self.shares)
        
        self.price = TextInput(
            label="委託價格",
            placeholder=f"當前價格: {current_price}，允許±10%",
            min_length=1,
            max_length=10,
            required=True
        )
        self.add_item(self.price)

    
    async def on_submit(self, interaction: discord.Interaction):
        """提交處理"""
        try:
            shares = int(self.shares.value)
            price = float(self.price.value)
            
            if shares <= 0:
                raise ValueError("購買數量必須大於0！")
            
            if price <= 0:
                raise ValueError("委託價格必須大於0！")
            
            # 執行購買
            stock_system = Stock(interaction.client)
            success, message = await stock_system.place_order(
                interaction.user.id, 
                self.stock_code, 
                "buy", 
                shares, 
                price
            )
            
            if success:
                embed = discord.Embed(
                    title="✅ 委託單提交成功",
                    description=message,
                    color=discord.Color.green()
                )
                embed.add_field(name="股票", value=f"{self.stock_name} ({self.stock_code})")
                embed.add_field(name="數量", value=f"{shares} 股")
                embed.add_field(name="委託價格", value=f"{price} Silva幣")
                embed.add_field(name="總花費", value=f"{shares * price:,.2f} Silva幣")
                
                await interaction.response.send_message(embed=embed, ephemeral=False)
            else:
                embed = discord.Embed(
                    title="❌ 委託單提交失敗",
                    description=message,
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
        except ValueError as e:
            await interaction.response.send_message(f"輸入錯誤：{str(e)}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"發生錯誤：{str(e)}", ephemeral=True)

class SellStockModal(Modal):
    """賣出股票對話框"""
    def __init__(self, stock_code, stock_name, current_price, available_shares):
        super().__init__(title=f"賣出 {stock_code} 股票")
        self.stock_code = stock_code
        self.stock_name = stock_name
        self.current_price = current_price
        self.available_shares = available_shares
        
        self.shares = TextInput(
            label="賣出數量",
            placeholder=f"可賣出數量: {available_shares}",
            min_length=1,
            max_length=10,
            required=True
        )
        self.add_item(self.shares)
        
        self.price = TextInput(
            label="委託價格",
            placeholder=f"當前價格: {current_price}，允許±10%",
            min_length=1,
            max_length=10,
            required=True
        )
        self.add_item(self.price)
    
    async def on_submit(self, interaction: discord.Interaction):
        """提交處理"""
        try:
            shares = int(self.shares.value)
            price = float(self.price.value)
            
            if shares <= 0:
                raise ValueError("賣出數量必須大於0！")
            
            if shares > self.available_shares:
                raise ValueError(f"超出可賣出數量！(最多 {self.available_shares} 股)")
            
            if price <= 0:
                raise ValueError("委託價格必須大於0！")
            
            # 執行賣出
            stock_system = Stock(interaction.client)
            success, message = await stock_system.place_order(
                interaction.user.id, 
                self.stock_code, 
                "sell", 
                shares, 
                price
            )
            
            if success:
                embed = discord.Embed(
                    title="✅ 委託單提交成功",
                    description=message,
                    color=discord.Color.green()
                )
                embed.add_field(name="股票", value=f"{self.stock_name} ({self.stock_code})")
                embed.add_field(name="數量", value=f"{shares} 股")
                embed.add_field(name="委託價格", value=f"{price} Silva幣")
                embed.add_field(name="預期收入", value=f"{shares * price:,.2f} Silva幣")
                
                await interaction.response.send_message(embed=embed, ephemeral=False)
            else:
                embed = discord.Embed(
                    title="❌ 委託單提交失敗",
                    description=message,
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
        except ValueError as e:
            await interaction.response.send_message(f"輸入錯誤：{str(e)}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"發生錯誤：{str(e)}", ephemeral=True)

class IssueStockModal(Modal):
    """發行股票對話框"""
    def __init__(self):
        super().__init__(title="發行新股票")
        
        self.stock_code = TextInput(
            label="股票代號",
            placeholder="例如: APPL, GOOG (2-10個字元)",
            min_length=2,
            max_length=10,
            required=True
        )
        self.add_item(self.stock_code)
        
        self.stock_name = TextInput(
            label="股票名稱",
            placeholder="公司全名 (2-20個字元)",
            min_length=2,
            max_length=20,
            required=True
        )
        self.add_item(self.stock_name)
        
        self.price = TextInput(
            label="初始價格",
            placeholder="每股價格 (最低1.0 Silva幣)",
            min_length=1,
            max_length=10,
            required=True
        )
        self.add_item(self.price)
        
        self.shares = TextInput(
            label="發行股數",
            placeholder="總發行股數 (最少100股)",
            min_length=1,
            max_length=10,
            required=True
        )
        self.add_item(self.shares)
        
        self.description = TextInput(
            label="公司描述",
            placeholder="公司的簡短描述 (最多100字)",
            style=discord.TextStyle.paragraph,
            max_length=100,
            required=True
        )
        self.add_item(self.description)
    
    async def on_submit(self, interaction: discord.Interaction):
        """提交處理"""
        try:
            stock_code = self.stock_code.value.upper()
            stock_name = self.stock_name.value
            price = float(self.price.value)
            shares = int(self.shares.value)
            description = self.description.value
            
            if price < 1.0:
                raise ValueError("初始價格必須至少為1.0 Silva幣！")
            
            if shares < 100:
                raise ValueError("發行股數必須至少為100股！")
            
            # 發行股票
            stock_system = Stock(interaction.client)
            success, message = await stock_system.issue_stock(
                interaction.user.id,
                stock_code,
                stock_name,
                price,
                shares,
                description
            )
            
            if success:
                issue_cost = price * shares * 0.05  # 發行費用為股票總價值的5%
                
                embed = discord.Embed(
                    title="✅ 股票發行成功",
                    description=message,
                    color=discord.Color.green()
                )
                embed.add_field(name="股票代號", value=stock_code)
                embed.add_field(name="股票名稱", value=stock_name)
                embed.add_field(name="初始價格", value=f"{price} Silva幣")
                embed.add_field(name="發行股數", value=f"{shares} 股")
                embed.add_field(name="總市值", value=f"{price * shares:,.2f} Silva幣")
                embed.add_field(name="發行費用", value=f"{issue_cost:,.2f} Silva幣")
                embed.add_field(name="描述", value=description, inline=False)
                
                await interaction.response.send_message(embed=embed, ephemeral=False)
            else:
                embed = discord.Embed(
                    title="❌ 股票發行失敗",
                    description=message,
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
        except ValueError as e:
            await interaction.response.send_message(f"輸入錯誤：{str(e)}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"發生錯誤：{str(e)}", ephemeral=True)

class DividendModal(Modal):
    """派發股息對話框"""
    def __init__(self, stock_code, stock_name):
        super().__init__(title=f"派發 {stock_code} 股息")
        self.stock_code = stock_code
        self.stock_name = stock_name
        
        self.amount = TextInput(
            label="每股股息金額",
            placeholder="每股派發的Silva幣金額",
            min_length=1,
            max_length=10,
            required=True
        )
        self.add_item(self.amount)
    
    async def on_submit(self, interaction: discord.Interaction):
        """提交處理"""
        try:
            amount = float(self.amount.value)
            
            if amount <= 0:
                raise ValueError("股息金額必須大於0！")
            
            # 派發股息
            stock_system = Stock(interaction.client)
            success, message = await stock_system.pay_dividend(
                interaction.user.id,
                self.stock_code,
                amount
            )
            
            if success:
                embed = discord.Embed(
                    title="✅ 股息派發成功",
                    description=message,
                    color=discord.Color.green()
                )
                
                await interaction.response.send_message(embed=embed, ephemeral=False)
            else:
                embed = discord.Embed(
                    title="❌ 股息派發失敗",
                    description=message,
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
        except ValueError as e:
            await interaction.response.send_message(f"輸入錯誤：{str(e)}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"發生錯誤：{str(e)}", ephemeral=True)

class StockCog(commands.Cog):
    """股票系統指令"""

    def __init__(self, bot):
        self.bot = bot
        self.stock = Stock(bot)
        self.currency = Currency(bot)
        # 啟動股票價格更新任務
        self.update_stock_prices.start()
    
    def cog_unload(self):
        """Cog卸載時停止任務"""
        self.update_stock_prices.cancel()
    # 先定義分頁視圖類
class StockPaginationView(discord.ui.View):
    def __init__(self, cog, current_page, total_pages):
        super().__init__(timeout=180)
        self.cog = cog
        self.current_page = current_page
        self.total_pages = total_pages
        
        # 添加上一頁按鈕
        self.prev_button = discord.ui.Button(
            label="上一頁", 
            style=discord.ButtonStyle.primary,
            disabled=(current_page <= 1),
            custom_id="prev_page"
        )
        self.prev_button.callback = self.previous_page
        self.add_item(self.prev_button)
        
        # 添加下一頁按鈕
        self.next_button = discord.ui.Button(
            label="下一頁", 
            style=discord.ButtonStyle.primary,
            disabled=(current_page >= total_pages),
            custom_id="next_page"
        )
        self.next_button.callback = self.next_page
        self.add_item(self.next_button)
    
    async def previous_page(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self.cog._show_stocks_page(interaction, self.current_page - 1)
        
    async def next_page(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self.cog._show_stocks_page(interaction, self.current_page + 1)


# 然後在 StockCog 類中定義方法
class StockCog(commands.Cog):


    async def _show_stocks_page(self, interaction, page: int = 1):
        """顯示股票市場的特定頁"""
        try:
            page = max(1, page)  # 確保頁碼至少為1
            page_size = 5  # 每頁顯示5個股票
            
            # 獲取分頁數據和總計
            stocks = await Stock.get_stocks_paged(page_size, page)
            total_count = await Stock.get_total_stocks_count()
            total_pages = (total_count + page_size - 1) // page_size  # 計算總頁數
            
            if not stocks:
                if page > 1:
                    await interaction.followup.send(f"頁碼 {page} 超出範圍，股票數據共有 {total_pages} 頁", ephemeral=True)
                else:
                    await interaction.followup.send("目前還沒有任何股票！使用 `/issuestock` 來發行新股票。", ephemeral=True)
                return
            
            embed = discord.Embed(
                title="📈 股票市場",
                description=f"所有可交易的股票列表 (第 {page}/{total_pages} 頁)",
                color=discord.Color.blue()
            )
            
            # 添加股票信息
            for stock_id, code, name, price, total_shares, issuer_id in stocks:
                try:
                    issuer = await self.bot.fetch_user(issuer_id)
                    issuer_name = issuer.name
                except:
                    issuer_name = f"未知用戶 (ID: {issuer_id})"
                    
                embed.add_field(
                    name=f"{code} - {name}",
                    value=f"價格: {price} Silva幣\n總股數: {total_shares:,} 股\n總市值: {price * total_shares:,.2f} Silva幣\n發行人: {issuer_name}",
                    inline=True
                )
            
            # 添加導航按鈕
            view = StockPaginationView(self, page, total_pages)
            
            if hasattr(interaction, 'response') and hasattr(interaction.response, 'is_done'):
                if interaction.response.is_done():
                    await interaction.followup.send(embed=embed, view=view)
                else:
                    await interaction.response.send_message(embed=embed, view=view)
            else:
                # 如果是編輯消息
                await interaction.edit(embed=embed, view=view)
        except Exception as e:
            print(f"顯示股票頁面時發生錯誤: {e}")
            try:
                if hasattr(interaction, 'followup'):
                    await interaction.followup.send("獲取股票市場資訊時發生錯誤，請通知管理員檢查。", ephemeral=True)
            except:
                print(f"無法發送錯誤信息: {e}")

    @app_commands.command(name="stocks", description="查看股票市場")
    @app_commands.describe(page="頁碼 (從1開始)")
    async def stocks(self, interaction: discord.Interaction, page: int = 1):
        """查看股票市場"""
        await interaction.response.defer(thinking=True)
        await self._show_stocks_page(interaction, page)

    @app_commands.command(name="stock", description="查看特定股票詳情")
    @app_commands.describe(stock_code="股票代號")
    async def stock(self, interaction: discord.Interaction, stock_code: str):
        """查看特定股票詳情"""
        try:
            # 轉換為大寫
            stock_code = stock_code.upper()
            
            # 獲取股票信息
            stock_info = await self.stock.get_stock_info(stock_code)
            
            if not stock_info:
                await interaction.response.send_message(f"找不到股票 {stock_code}！", ephemeral=True)
                return
            
            # 獲取股東資訊
            shareholders = await self.stock.get_stock_shareholders(stock_code, 5)
            
            # 獲取價格歷史
            price_history = await self.stock.get_price_history(stock_code, 7)
            
            # 創建嵌入訊息
            embed = discord.Embed(
                title=f"📊 {stock_info['stock_name']} ({stock_code})",
                description=stock_info['description'],
                color=discord.Color.blue()
            )
            
            # 基本資訊
            embed.add_field(name="當前價格", value=f"{stock_info['price']} Silva幣", inline=True)
            embed.add_field(name="初始價格", value=f"{stock_info['initial_price']} Silva幣", inline=True)
            
            # 計算漲跌幅
            price_change = ((stock_info['price'] / stock_info['initial_price']) - 1) * 100
            change_symbol = "🟢" if price_change >= 0 else "🔴"
            embed.add_field(name="總漲跌幅", value=f"{change_symbol} {price_change:.2f}%", inline=True)
            
            embed.add_field(name="總股數", value=f"{stock_info['total_shares']:,} 股", inline=True)
            embed.add_field(name="總市值", value=f"{stock_info['price'] * stock_info['total_shares']:,.2f} Silva幣", inline=True)
            
            try:
                issuer = await self.bot.fetch_user(stock_info['issuer_id'])
                embed.add_field(name="發行人", value=issuer.mention, inline=True)
            except:
                embed.add_field(name="發行人", value=f"未知用戶 (ID: {stock_info['issuer_id']})", inline=True)
            
            # 股價歷史
            if price_history:
                history_text = ""
                for date, price in price_history:
                    history_text += f"{date}: {price} Silva幣\n"
                embed.add_field(name="近期價格歷史", value=history_text, inline=False)
            
            # 主要股東
            if shareholders:
                shareholders_text = ""
                for user_id, shares, percentage in shareholders:
                    try:
                        user = await self.bot.fetch_user(user_id)
                        shareholders_text += f"{user.mention}: {shares:,} 股 ({percentage}%)\n"
                    except:
                        shareholders_text += f"未知用戶 (ID: {user_id}): {shares:,} 股 ({percentage}%)\n"
                
                embed.add_field(name="主要股東", value=shareholders_text, inline=False)
            
            # 添加創建日期
            created_at = datetime.datetime.strptime(stock_info['created_at'], '%Y-%m-%d %H:%M:%S')
            embed.set_footer(text=f"發行日期: {created_at.strftime('%Y-%m-%d')}")
            
            # 添加按鈕
            view = discord.ui.View(timeout=180)
            
            # 使用者持有的股份
            user_holding = 0
            user_stocks = await self.stock.get_user_stocks(interaction.user.id)
            for stock_id, code, name, shares, price in user_stocks:
                if code == stock_code:
                    user_holding = shares
                    break
            
            buy_button = discord.ui.Button(label="買入", style=discord.ButtonStyle.green)
            async def buy_callback(interaction: discord.Interaction):
                await interaction.response.send_modal(BuyStockModal(stock_code, stock_info['stock_name'], stock_info['price']))
            buy_button.callback = buy_callback
            view.add_item(buy_button)
            
            if user_holding > 0:
                sell_button = discord.ui.Button(label=f"賣出 (持有: {user_holding}股)", style=discord.ButtonStyle.red)
                async def sell_callback(interaction: discord.Interaction):
                    await interaction.response.send_modal(
                        SellStockModal(stock_code, stock_info['stock_name'], stock_info['price'], user_holding)
                    )
                sell_button.callback = sell_callback
                view.add_item(sell_button)
            
            # 如果是股票發行人，添加派發股息按鈕
            if interaction.user.id == stock_info['issuer_id']:
                dividend_button = discord.ui.Button(label="派發股息", style=discord.ButtonStyle.blurple)
                async def dividend_callback(interaction: discord.Interaction):
                    await interaction.response.send_modal(DividendModal(stock_code, stock_info['stock_name']))
                dividend_button.callback = dividend_callback
                view.add_item(dividend_button)
            
            await interaction.response.send_message(embed=embed, view=view)
        except Exception as e:
            print(f"執行 stock 指令時發生錯誤: {e}")
            await interaction.response.send_message(f"獲取股票資訊時發生錯誤，請通知管理員檢查。", ephemeral=True)

    @app_commands.command(name="mystock", description="查看你持有的股票")
    async def my_stock(self, interaction: discord.Interaction):
        """查看你持有的股票"""
        try:
            # 獲取用戶持股
            stocks = await self.stock.get_user_stocks(interaction.user.id)
            
            if not stocks:
                await interaction.response.send_message("你目前沒有持有任何股票！", ephemeral=True)
                return
            
            embed = discord.Embed(
                title="📊 你的股票投資組合",
                color=discord.Color.blue()
            )
            
            total_value = 0
            
            for stock_id, code, name, shares, price in stocks:
                value = shares * price
                total_value += value
                
                embed.add_field(
                    name=f"{code} - {name}",
                    value=f"持有: {shares:,} 股\n價格: {price} Silva幣\n價值: {value:,.2f} Silva幣",
                    inline=True
                )
            
            embed.add_field(name="總投資價值", value=f"{total_value:,.2f} Silva幣", inline=False)
            
            # 獲取用戶餘額
            balance = await self.currency.get_balance(interaction.user.id)
            embed.set_footer(text=f"現金餘額: {balance:,} Silva幣 | 總資產: {balance + total_value:,.2f} Silva幣")
            
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            print(f"執行 mystock 指令時發生錯誤: {e}")
            await interaction.response.send_message(f"獲取持股資訊時發生錯誤，請通知管理員檢查。", ephemeral=True)

    @app_commands.command(name="orders", description="查看你的委託單")
    @app_commands.describe(active_only="是否只顯示活躍的委託單")
    async def orders(self, interaction: discord.Interaction, active_only: bool = True):
        """查看你的委託單"""
        try:
            # 獲取用戶委託單
            orders = await self.stock.get_user_orders(interaction.user.id, active_only)
            
            if not orders:
                message = "你目前沒有活躍的委託單！" if active_only else "你沒有任何委託單歷史！"
                await interaction.response.send_message(message, ephemeral=True)
                return
            
            embed = discord.Embed(
                title="📝 你的股票委託單",
                description="以下是你的委託單列表" + (" (只顯示活躍的)" if active_only else ""),
                color=discord.Color.blue()
            )
            
            # 創建視圖用於取消委託單
            view = discord.ui.View(timeout=180)
            
            for i, (order_id, stock_code, stock_name, order_type, shares, price, status, created_at) in enumerate(orders):
                type_emoji = "🟢" if order_type == "buy" else "🔴"
                type_text = "購買" if order_type == "buy" else "出售"
                status_text = "活躍" if status == "active" else ("已完成" if status == "completed" else "已取消")
                
                created_at_time = datetime.datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S')
                time_str = created_at_time.strftime('%Y-%m-%d %H:%M')
                
                embed.add_field(
                    name=f"#{order_id}: {type_emoji} {type_text} {stock_code}",
                    value=f"股票: {stock_name}\n數量: {shares} 股\n價格: {price} Silva幣\n總額: {shares * price:,.2f} Silva幣\n狀態: {status_text}\n提交時間: {time_str}",
                    inline=True
                )
                
                # 為活躍的委託單添加取消按鈕
                if status == "active" and i < 5:  # 限制按鈕數量為前5個
                    cancel_button = discord.ui.Button(label=f"取消 #{order_id}", style=discord.ButtonStyle.red, custom_id=f"cancel_{order_id}")
                    
                    async def create_cancel_callback(order_id):
                        async def cancel_callback(interaction: discord.Interaction):
                            success, message = await self.stock.cancel_order(interaction.user.id, order_id)
                            
                            if success:
                                embed = discord.Embed(
                                    title="✅ 委託單已取消",
                                    description=message,
                                    color=discord.Color.green()
                                )
                                await interaction.response.send_message(embed=embed, ephemeral=False)
                            else:
                                embed = discord.Embed(
                                    title="❌ 取消失敗",
                                    description=message,
                                    color=discord.Color.red()
                                )
                                await interaction.response.send_message(embed=embed, ephemeral=True)
                        
                        return cancel_callback
                    
                    cancel_button.callback = await create_cancel_callback(order_id)
                    view.add_item(cancel_button)
            
            # 如果沒有活躍訂單，不顯示視圖
            has_active = any(status == "active" for _, _, _, _, _, _, status, _ in orders)
            
            await interaction.response.send_message(
                embed=embed, 
                view=view if has_active else None
            )
        except Exception as e:
            print(f"執行 orders 指令時發生錯誤: {e}")
            await interaction.response.send_message(f"獲取委託單資訊時發生錯誤，請通知管理員檢查。", ephemeral=True)

    @app_commands.command(name="buystock", description="購買股票")
    @app_commands.describe(stock_code="股票代號")
    async def buy_stock(self, interaction: discord.Interaction, stock_code: str):
        """購買股票"""
        try:
            # 轉換為大寫
            stock_code = stock_code.upper()
            
            # 獲取股票信息
            stock_info = await self.stock.get_stock_info(stock_code)
            
            if not stock_info:
                await interaction.response.send_message(f"找不到股票 {stock_code}！", ephemeral=True)
                return
            
            # 顯示購買對話框
            await interaction.response.send_modal(
                BuyStockModal(stock_code, stock_info['stock_name'], stock_info['price'])
            )
        except Exception as e:
            print(f"執行 buystock 指令時發生錯誤: {e}")
            await interaction.response.send_message(f"準備購買股票時發生錯誤，請通知管理員檢查。", ephemeral=True)

    @app_commands.command(name="sellstock", description="賣出股票")
    @app_commands.describe(stock_code="股票代號")
    async def sell_stock(self, interaction: discord.Interaction, stock_code: str):
        """賣出股票"""
        try:
            # 轉換為大寫
            stock_code = stock_code.upper()
            
            # 獲取股票信息
            stock_info = await self.stock.get_stock_info(stock_code)
            
            if not stock_info:
                await interaction.response.send_message(f"找不到股票 {stock_code}！", ephemeral=True)
                return
            
            # 檢查用戶持股
            user_stocks = await self.stock.get_user_stocks(interaction.user.id)
            user_holding = 0
            
            for stock_id, code, name, shares, price in user_stocks:
                if code == stock_code:
                    user_holding = shares
                    break
            
            if user_holding <= 0:
                await interaction.response.send_message(f"你沒有持有 {stock_code} 的股票！", ephemeral=True)
                return
            
            # 顯示賣出對話框
            await interaction.response.send_modal(
                SellStockModal(stock_code, stock_info['stock_name'], stock_info['price'], user_holding)
            )
        except Exception as e:
            print(f"執行 sellstock 指令時發生錯誤: {e}")
            await interaction.response.send_message(f"準備賣出股票時發生錯誤，請通知管理員檢查。", ephemeral=True)

    @app_commands.command(name="issuestock", description="發行新股票")
    async def issue_stock(self, interaction: discord.Interaction):
        """發行新股票"""
        try:
            await interaction.response.send_modal(IssueStockModal())
        except Exception as e:
            print(f"執行 issuestock 指令時發生錯誤: {e}")
            await interaction.response.send_message(f"準備發行股票時發生錯誤，請通知管理員檢查。", ephemeral=True)

    @app_commands.command(name="topstocks", description="查看漲幅最高的股票")
    async def top_stocks(self, interaction: discord.Interaction):
        """查看漲幅最高的股票"""
        try:
            # 獲取排名靠前的股票
            top_stocks = await self.stock.get_top_stocks(5)
            
            if not top_stocks:
                await interaction.response.send_message("目前還沒有任何股票交易記錄！", ephemeral=True)
                return
            
            embed = discord.Embed(
                title="🏆 股票漲幅排行榜",
                description="以下是漲幅最高的股票",
                color=discord.Color.gold()
            )
            
            for stock_code, stock_name, price, change_percent in top_stocks:
                change_symbol = "🟢" if change_percent >= 0 else "🔴"
                
                embed.add_field(
                    name=f"{change_symbol} {stock_code} - {stock_name}",
                    value=f"當前價格: {price} Silva幣\n漲跌幅: {change_percent}%",
                    inline=True
                )
            
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            print(f"執行 topstocks 指令時發生錯誤: {e}")
            await interaction.response.send_message(f"獲取股票排行榜時發生錯誤，請通知管理員檢查。", ephemeral=True)

    @app_commands.command(name="dividend", description="為你發行的股票派發股息")
    @app_commands.describe(stock_code="股票代號")
    async def dividend(self, interaction: discord.Interaction, stock_code: str):
        """為你發行的股票派發股息"""
        try:
            # 轉換為大寫
            stock_code = stock_code.upper()
            
            # 獲取股票信息
            stock_info = await self.stock.get_stock_info(stock_code)
            
            if not stock_info:
                await interaction.response.send_message(f"找不到股票 {stock_code}！", ephemeral=True)
                return
            
            # 檢查是否為發行人
            if stock_info['issuer_id'] != interaction.user.id:
                await interaction.response.send_message("只有股票發行人可以宣布派發股息！", ephemeral=True)
                return
            
            # 顯示派息對話框
            await interaction.response.send_modal(DividendModal(stock_code, stock_info['stock_name']))
        except Exception as e:
            print(f"執行 dividend 指令時發生錯誤: {e}")
            await interaction.response.send_message(f"準備派發股息時發生錯誤，請通知管理員檢查。", ephemeral=True)

    @app_commands.command(name="stockhelp", description="獲取股票系統使用幫助")
    async def stock_help(self, interaction: discord.Interaction):
        """獲取股票系統使用幫助"""
        embed = discord.Embed(
            title="📈 股票系統使用指南",
            description="這是一個完整的股票交易系統，讓你可以發行、買賣股票和派發股息。",
            color=discord.Color.blue()
        )
        
        commands_text = """
        `/stocks` - 查看所有可交易的股票列表
        `/stock [代號]` - 查看特定股票的詳細資訊
        `/mystock` - 查看你持有的所有股票
        `/orders [active_only]` - 查看你的委託單，預設只顯示活躍的
        `/buystock [代號]` - 購買特定股票
        `/sellstock [代號]` - 賣出特定股票
        `/issuestock` - 發行你自己的股票
        `/dividend [代號]` - 為你發行的股票派發股息
        `/topstocks` - 查看漲幅最高的股票
        """
        
        embed.add_field(name="可用指令", value=commands_text, inline=False)
        
        features_text = """
        - **發行股票**: 任何玩家都可以發行自己的股票，但需支付發行費用(總市值5%)
        - **買賣股票**: 股票價格基於最後成交價，有±10%的每日漲跌停限制
        - **派發股息**: 股票發行人可以隨時派發股息給所有股東
        - **委託單系統**: 買賣委託會自動撮合，按價格優先順序成交
        """
        
        embed.add_field(name="系統特點", value=features_text, inline=False)
        
        tips_text = """
        - 🔍 投資前先研究: 查看股票資訊、股東結構和價格歷史
        - 💰 分散投資: 不要把所有資金都投入單一股票
        - 📊 追蹤漲幅: 使用`/topstocks`找出表現良好的股票
        - 💎 股息收入: 持有有派息歷史的股票可獲得被動收入
        - ⏱️ 耐心等待: 委託單如果價格合理，最終會有人成交
        """
        
        embed.add_field(name="投資小技巧", value=tips_text, inline=False)
        
        await interaction.response.send_message(embed=embed)

    @tasks.loop(hours=1)  # 每小時更新一次
    async def update_stock_prices(self):
        """每小時更新股票價格，添加一些隨機波動"""
        try:
            # 獲取所有股票
            stocks = await self.stock.get_all_stocks()
            
            for stock_id, code, name, price, total_shares, issuer_id in stocks:
                # 生成-3%到+3%的隨機波動
                change_percent = (random.random() * 0.06 - 0.03)
                new_price = price * (1 + change_percent)
                
                # 確保波動在漲跌停範圍內
                price_limit_low = price * (1 - self.stock.price_change_limit)
                price_limit_high = price * (1 + self.stock.price_change_limit)
                new_price = max(price_limit_low, min(new_price, price_limit_high))
                
                # 更新價格
                await self.stock.update_stock_price_directly(stock_id, new_price)
                
                print(f"已更新股票 {code} 價格: {price} -> {new_price} ({change_percent*100:+.2f}%)")
        except Exception as e:
            print(f"更新股票價格時發生錯誤: {e}")

    @update_stock_prices.before_loop
    async def before_update_stock_prices(self):
        """等待機器人準備好後再開始任務"""
        await self.bot.wait_until_ready()

    # 以下是管理員用於診斷問題的指令
    @app_commands.command(name="check_stock_db", description="檢查股票資料庫狀態 (管理員專用)")
    @app_commands.default_permissions(administrator=True)
    async def check_stock_db(self, interaction: discord.Interaction):
        """檢查股票資料庫狀態"""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("你沒有權限使用此指令！", ephemeral=True)
            return
            
        try:
            # 獲取資料庫連接
            conn = await get_db_connection(self.stock.db_name)
            cursor = await conn.cursor()
            
            # 檢查所有表格
            tables = ["stocks", "stock_holdings", "stock_transactions", "stock_dividends", "stock_price_history", "stock_orders"]
            table_status = {}
            
            for table in tables:
                try:
                    await cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = await cursor.fetchone()
                    table_status[table] = count[0] if count else 0
                except Exception as e:
                    table_status[table] = f"錯誤: {str(e)}"
            
            # 創建嵌入訊息
            embed = discord.Embed(
                title="📊 股票資料庫狀態",
                color=discord.Color.blue()
            )
            
            for table, status in table_status.items():
                embed.add_field(name=table, value=str(status), inline=True)
                
            await interaction.response.send_message(embed=embed, ephemeral=False)
        except Exception as e:
            print(f"檢查股票資料庫時發生錯誤: {e}")
            await interaction.response.send_message(f"檢查股票資料庫時發生錯誤: {str(e)}", ephemeral=True)

    # @app_commands.command(name="reset_stock_db", description="重置股票資料庫 (管理員專用)")
    # @app_commands.default_permissions(administrator=True)
    # async def reset_stock_db(self, interaction: discord.Interaction):
    #     """重置股票資料庫"""
    #     if not interaction.user.guild_permissions.administrator:
    #         await interaction.response.send_message("你沒有權限使用此指令！", ephemeral=True)
    #         return
            
    #     try:
    #         # 獲取資料庫連接
    #         conn = await get_db_connection(self.stock.db_name)
    #         cursor = await conn.cursor()
            
    #         # 刪除所有表格
    #         tables = ["stocks", "stock_holdings", "stock_transactions", "stock_dividends", "stock_price_history", "stock_orders"]
    #         for table in tables:
    #             await cursor.execute(f"DROP TABLE IF EXISTS {table}")
                
    #         await conn.commit()
            
    #         # 重新創建表格
    #         await self.stock.setup_database()
            
    #         await interaction.response.send_message("✅ 股票資料庫已重置！", ephemeral=False)
    #     except Exception as e:
    #         print(f"重置股票資料庫時發生錯誤: {e}")
    #         await interaction.response.send_message(f"重置股票資料庫時發生錯誤: {str(e)}", ephemeral=True)

    @app_commands.command(name="update_stock_prices_now", description="立即更新所有股票價格 (管理員專用)")
    @app_commands.default_permissions(administrator=True)
    async def update_stock_prices_now(self, interaction: discord.Interaction):
        """立即更新所有股票價格"""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("你沒有權限使用此指令！", ephemeral=True)
            return
            
        try:
            await interaction.response.defer(thinking=True)
            
            # 執行價格更新
            await self.update_stock_prices()
            
            await interaction.followup.send("✅ 已成功更新所有股票價格！")
        except Exception as e:
            print(f"立即更新股票價格時發生錯誤: {e}")
            await interaction.followup.send(f"更新股票價格時發生錯誤: {str(e)}")

async def setup(bot):
    await bot.add_cog(StockCog(bot))