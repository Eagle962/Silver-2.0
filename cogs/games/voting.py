import datetime
import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Button, View
import asyncio

class VoteButton(Button):
    """投票按鈕"""
    def __init__(self, option: str, vote_data: dict):
        super().__init__(
            label=f"{option} (0)",
            style=discord.ButtonStyle.primary,
            custom_id=f"vote_{option}"
        )
        self.option = option
        self.vote_data = vote_data
        self.vote_data[option] = set()  # 使用集合來儲存投票者的ID

    async def callback(self, interaction: discord.Interaction):
        """按鈕回調函數"""
        user_id = interaction.user.id

        # 檢查用戶是否已經在其他選項投票
        for opt, voters in self.vote_data.items():
            if user_id in voters and opt != self.option:
                voters.remove(user_id)
                # 更新其他按鈕的顯示
                for child in self.view.children:
                    if child.custom_id == f"vote_{opt}":
                        child.label = f"{opt} ({len(voters)})"

        # 處理當前選項的投票
        if user_id in self.vote_data[self.option]:
            self.vote_data[self.option].remove(user_id)
            await interaction.response.send_message(f"你取消了對 {self.option} 的投票", ephemeral=True)
        else:
            self.vote_data[self.option].add(user_id)
            await interaction.response.send_message(f"你投票給了 {self.option}", ephemeral=True)

        # 更新按鈕顯示
        self.label = f"{self.option} ({len(self.vote_data[self.option])})"
        await interaction.message.edit(view=self.view)

class VoteView(View):
    """投票視圖"""
    def __init__(self, options: list):
        super().__init__(timeout=None)
        self.vote_data = {}
        
        # 創建每個選項的按鈕
        for option in options:
            button = VoteButton(option, self.vote_data)
            self.add_item(button)

class VotingCog(commands.Cog):
    """投票系統指令"""

    def __init__(self, bot):
        self.bot = bot
        self.active_votes = {}  # 儲存活動中的投票

    @app_commands.command(name="vote", description="創建一個投票")
    @app_commands.describe(
        title="投票標題",
        options="投票選項（用斜線/分隔）",
        duration="投票持續時間（分鐘，若不設置則永久有效）"
    )
    async def vote(
        self,
        interaction: discord.Interaction,
        title: str,
        options: str,
        duration: int = None
    ):
        """
        創建一個投票
        參數:
            title: 投票標題
            options: 投票選項，用斜線分隔
            duration: 投票持續時間（分鐘）
        """
        try:
            # 分割選項
            option_list = [opt.strip() for opt in options.split('/')]
            
            # 檢查選項數量
            if len(option_list) < 2:
                await interaction.response.send_message("至少需要2個選項！", ephemeral=True)
                return
            if len(option_list) > 5:
                await interaction.response.send_message("最多只能有5個選項！", ephemeral=True)
                return

            # 創建投票視圖
            view = VoteView(option_list)
            
            # 創建投票訊息
            embed = discord.Embed(
                title=f"📊 {title}",
                description="點擊下方按鈕進行投票！",
                color=discord.Color.blue()
            )
            embed.add_field(name="創建者", value=interaction.user.mention)
            if duration:
                embed.add_field(name="結束時間", value=f"{duration}分鐘後")
                
            # 發送投票訊息
            await interaction.response.send_message(embed=embed, view=view)

            # 如果設置了持續時間，設定定時器來結束投票
            if duration:
                original_message = await interaction.original_response()
                
                # 保存活動投票
                self.active_votes[original_message.id] = {
                    "view": view,
                    "title": title,
                    "options": option_list,
                    "end_time": discord.utils.utcnow() + datetime.timedelta(minutes=duration)
                }
                
                # 啟動結束投票任務
                self.bot.loop.create_task(self.end_vote_after_duration(original_message.id, duration))

        except Exception as e:
            await interaction.response.send_message(
                f"創建投票失敗！錯誤訊息: {str(e)}",
                ephemeral=True
            )

    async def end_vote_after_duration(self, message_id, duration):
        """結束投票任務"""
        await asyncio.sleep(duration * 60)  # 轉換為秒
        
        if message_id not in self.active_votes:
            return
            
        vote_data = self.active_votes[message_id]
        view = vote_data["view"]
        title = vote_data["title"]
        option_list = vote_data["options"]
        
        try:
            # 嘗試取得訊息
            channel_id = None
            message = None
            
            for ch in self.bot.get_all_channels():
                try:
                    message = await ch.fetch_message(message_id)
                    if message:
                        channel_id = ch.id
                        break
                except:
                    pass
                    
            if not message:
                del self.active_votes[message_id]
                return
                
            # 計算結果
            results = []
            for option in option_list:
                vote_count = len(view.vote_data.get(option, set()))
                results.append((option, vote_count))
            
            # 排序結果
            results.sort(key=lambda x: x[1], reverse=True)
            
            # 創建結果嵌入訊息
            result_embed = discord.Embed(
                title=f"📊 投票結果：{title}",
                description="投票已結束！",
                color=discord.Color.green()
            )
            
            for option, count in results:
                result_embed.add_field(
                    name=option,
                    value=f"票數：{count}",
                    inline=False
                )
                
            await message.edit(embed=result_embed, view=None)
            del self.active_votes[message_id]
            
        except Exception as e:
            print(f"結束投票時發生錯誤: {e}")
            
            try:
                del self.active_votes[message_id]
            except:
                pass

async def setup(bot):
    await bot.add_cog(VotingCog(bot))