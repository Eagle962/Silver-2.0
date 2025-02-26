import random
from typing import List, Optional, Dict, Set

# 卡牌遊戲相關類別
class Card:
    """卡牌類別"""
    def __init__(self, suit: str, value: str):
        self.suit = suit
        self.value = value
        
    def __str__(self):
        suit_emoji = {
            "♠": "♠️",
            "♥": "♥️",
            "♦": "♦️",
            "♣": "♣️"
        }
        return f"{suit_emoji[self.suit]}{self.value}"

class Deck:
    """牌組類別"""
    def __init__(self):
        suits = ["♠", "♥", "♦", "♣"]
        values = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
        self.cards = [Card(suit, value) for suit in suits for value in values]
        random.shuffle(self.cards)
        
    def draw(self) -> Optional[Card]:
        """抽一張牌"""
        if not self.cards:
            return None
        return self.cards.pop()

class Hand:
    """手牌類別"""
    def __init__(self):
        self.cards: List[Card] = []
        
    def add_card(self, card: Card):
        """添加一張牌到手牌"""
        self.cards.append(card)
        
    def get_value(self) -> int:
        """計算手牌點數"""
        value = 0
        aces = 0
        
        for card in self.cards:
            if card.value in ["J", "Q", "K"]:
                value += 10
            elif card.value == "A":
                aces += 1
            else:
                value += int(card.value)
                
        for _ in range(aces):
            if value + 11 <= 21:
                value += 11
            else:
                value += 1
                
        return value
    
    def __str__(self) -> str:
        """返回手牌字串表示"""
        return " ".join(str(card) for card in self.cards)

# 賽馬遊戲相關類別
class Horse:
    """馬匹類別"""
    def __init__(self, name: str, emoji: str, number: int):
        self.name = name
        self.emoji = emoji
        self.number = number
        self.position = 0
        self.finished = False
        self.special_event = None

class HorseRace:
    """賽馬模型"""
    def __init__(self, bot):
        self.bot = bot
        self.is_race_active = False
        self.betting_open = False
        self.bets: Dict[int, Dict[int, int]] = {}  # {user_id: {horse_number: amount}}
        self.horses = [
            Horse("damn", "🐎", 1),
            Horse("gayco", "🏃", 2),
            Horse("origaymi", "💨", 3),
            Horse("gayzi", "🔥", 4),
            Horse("ray", "⚡", 5)
        ]
        self.race_channel = None
        self.track_length = 20
        self.special_events = [
            "突然加速！向前衝了3格！",
            "被絆了一下...後退1格",
            "獲得了觀眾的加油！速度提升！",
            "踩到香蕉皮，滑倒了...",
            "喝了能量飲料！充滿力量！",
            "遇到蕃薯攤誘惑，停下來買蕃薯...",
            "被附近的狗嚇到了！",
            "遇到小水漥，不得不繞路",
            "吃到飼料補給，恢復體力！",
            "被蜜蜂追趕，速度大增！"
        ]
        
    def place_bet(self, user_id: int, horse_number: int, amount: int) -> bool:
        """玩家下注"""
        if not self.betting_open:
            return False
            
        if horse_number < 1 or horse_number > len(self.horses):
            return False

        if user_id not in self.bets:
            self.bets[user_id] = {}
        
        self.bets[user_id][horse_number] = amount
        return True