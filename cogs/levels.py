import discord
from discord.ext import commands
from discord import app_commands
from models.levels import LevelSystem
from config import get_config_value

class LevelsCog(commands.Cog):
    """等級系統指令"""

    def __init__(self, bot):
        self.bot = bot
        self.level_system = LevelSystem(bot)

    @commands.Cog.listener()
    async def on_message(self, message):
        """監聽訊息事件並增加經驗值"""
        # 忽略機器人訊息
        if message.author.bot:
            return
            
        # 增加經驗值
        new_level = await self.level_system.add_exp(message.author.id)
        
        # 如果升級了，發送通知
        if new_level is not None:
            try:
                # 從配置中獲取等級通知頻道
                level_channel_id = get_config_value('level_channel')
                if level_channel_id:
                    level_channel = self.bot.get_channel(level_channel_id)
                    if level_channel:
                        await level_channel.send(f"🎉 恭喜 {message.author.mention} 升到 {new_level} 等了!")
                    else:
                        print(f"找不到頻道 ID: {level_channel_id}")
            except Exception as e:
                print(f"發送升級訊息時發生錯誤: {e}")

    @app_commands.command(name="level", description="查看等級資訊")
    async def level(self, interaction: discord.Interaction):
        """查看你的等級資訊"""
        stats = await self.level_system.get_user_stats(interaction.user.id)
        
        if stats:
            embed = discord.Embed(
                title=f"📊 {interaction.user.display_name} 的等級資訊",
                color=discord.Color.blue()
            )
            embed.add_field(name="等級", value=str(stats['level']), inline=True)
            embed.add_field(name="經驗值", 
                        value=f"{stats['exp']}/{stats['next_level_exp']}", 
                        inline=True)
            embed.add_field(name="總訊息數", 
                        value=str(stats['message_count']), 
                        inline=True)
            
            progress = (stats['exp'] / stats['next_level_exp']) * 100
            embed.add_field(name="升級進度", 
                        value=f"`{'■' * int(progress/10)}{'□' * (10-int(progress/10))}` {progress:.1f}%",
                        inline=False)
            
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("找不到你的等級資訊！", ephemeral=True)

    @app_commands.command(name="leaderboard", description="查看等級排行榜")
    async def leaderboard(self, interaction: discord.Interaction, limit: int = 10):
        """查看等級排行榜"""
        if limit < 1:
            limit = 10
        elif limit > 25:
            limit = 25
            
        leaderboard_data = await self.level_system.get_leaderboard(limit)
        
        if not leaderboard_data:
            await interaction.response.send_message("排行榜中沒有資料！", ephemeral=True)
            return
            
        embed = discord.Embed(
            title="📊 伺服器等級排行榜",
            description=f"前 {limit} 名玩家",
            color=discord.Color.blue()
        )
        
        # 添加排行榜數據
        for idx, (user_id, level, exp, message_count) in enumerate(leaderboard_data, 1):
            try:
                user = await self.bot.fetch_user(user_id)
                username = user.name
            except:
                username = f"未知用戶 (ID: {user_id})"
                
            next_level_exp = self.level_system.calculate_exp_for_next_level(level)
            
            embed.add_field(
                name=f"#{idx} {username}",
                value=f"等級: {level} | 經驗: {exp}/{next_level_exp} | 訊息: {message_count}",
                inline=False
            )
            
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="set_level", description="設定用戶等級 (管理員專用)")
    @app_commands.default_permissions(administrator=True)
    async def set_level(self, interaction: discord.Interaction, user: discord.Member, level: int):
        """設定用戶等級 (管理員專用)"""
        if level < 0:
            await interaction.response.send_message("等級不能小於0！", ephemeral=True)
            return
            
        # 獲取當前用戶統計資料
        current_stats = await self.level_system.get_user_stats(user.id)
        
        if not current_stats:
            # 如果用戶沒有記錄，先添加經驗值
            await self.level_system.add_exp(user.id, 0)
            current_stats = await self.level_system.get_user_stats(user.id)
            
        # 計算需要的經驗值
        exp_needed = 0
        for lvl in range(level):
            exp_needed += self.level_system.calculate_exp_for_next_level(lvl)
            
        # 直接更新數據庫
        conn = await self.level_system.get_db_connection(self.level_system.db_name)
        cursor = await conn.cursor()
        
        await cursor.execute(
            'UPDATE user_levels SET level = ?, exp = ? WHERE user_id = ?',
            (level, exp_needed, user.id)
        )
        
        await conn.commit()
        
        embed = discord.Embed(
            title="📊 等級設定成功",
            description=f"{user.mention} 的等級已設定為 **{level}**",
            color=discord.Color.green()
        )
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(LevelsCog(bot))