import discord
from discord.ext import commands
import json
import asyncio
import os
from config import load_config

# 設置機器人權限
intents = discord.Intents.default()
intents.invites = True
intents.message_content = True
intents.typing = True
intents.members = True
intents.reactions = True
intents.presences = True

# 初始化機器人
bot = commands.Bot(command_prefix='!', intents=intents)

# 載入設定
config = load_config()

# 全域變數 (可以考慮改成更好的管理方式)
currency_instance = None

@bot.event
async def on_ready():
    """機器人啟動時執行"""
    try:
        # 載入所有的 Cogs
        for folder in ['cogs', 'cogs/games']:
            for filename in os.listdir(folder):
                if filename.endswith('.py'):
                    await bot.load_extension(f'{folder.replace("/", ".")}.{filename[:-3]}')
                    print(f'已載入 {filename}')

        # 同步斜線指令
        synced = await bot.tree.sync()
        print(f"同步了 {len(synced)} 個指令")
        
        # 初始化持久化視圖 (可以移至 roles cog)
        await reload_persistent_views()
        
        # 設定狀態
        await bot.change_presence(
            activity=discord.Activity(type=discord.ActivityType.playing, name="SilvA"),
            status=discord.Status.do_not_disturb
        )
        print(f'機器人已上線 - {bot.user.name}')
    except Exception as e:
        print(f"初始化過程中發生錯誤: {e}")


async def reload_persistent_views():
    """重新載入持久化按鈕視圖"""
    try:
        persistent_views = {}
        
        for guild in bot.guilds:
            try:
                # 讀取該伺服器的持久化按鈕配置
                with open(f'role_buttons_{guild.id}.json', 'r', encoding='utf8') as f:
                    role_data = json.load(f)
                    
                    # 實際的視圖載入需要移至 roles cog
                    # 這裡只是佔位，實際實現時需要導入正確的類別
                    from cogs.roles import RoleButtonView
                    
                    for channel_id, roles in role_data.items():
                        view = RoleButtonView(roles)
                        persistent_views[int(channel_id)] = view
                        bot.add_view(view)
            except FileNotFoundError:
                continue  # 如果檔案不存在，跳過該伺服器
            except Exception as e:
                print(f"加載伺服器 {guild.id} 的持久化按鈕時出錯: {e}")
    except Exception as e:
        print(f"重新載入持久化視圖時發生錯誤: {e}")


@bot.event
async def on_member_join(member):
    """新成員加入時執行"""
    channel = bot.get_channel(config['welcome_channel'])
    await channel.send(f'歡迎 {member.mention} 加入')


@bot.event
async def on_member_remove(member):
    """成員離開時執行"""
    channel = bot.get_channel(config['welcome_channel'])
    await channel.send(f'幹 走了 {member}')


@bot.command()
async def check_commands(ctx):
    """檢查已註冊的斜線指令"""
    commands = await bot.tree.fetch_commands()
    response = "目前註冊的斜線指令：\n"
    for cmd in commands:
        response += f"- /{cmd.name}\n"
    await ctx.send(response)


if __name__ == "__main__":
    bot.run(config['Silva'])