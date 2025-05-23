# features/language_tutor.py

import random

class LanguageTutor:
    def __init__(self, memory):
        self.memory = memory

    def start(self, language="Japanese", level="beginner"):
        if language == "Japanese":
            return self._teach_japanese(level)
        elif language == "Mandarin":
            return self._teach_mandarin(level)
        else:
            return f"Sorry, I can't teach {language} yet."

    def quiz_vocabulary(self, language):
        vocab_list = self.memory.get_vocab(language)
        if not vocab_list:
            return "You haven't learned any words yet!"

        word = random.choice(vocab_list)
        native, translated = word.split(" - ")
        return f"What does '{native}' mean?"

    def _teach_japanese(self, level):
        if level == "beginner":
            vocab = ["こんにちは - Hello", "ありがとう - Thank you", "さようなら - Goodbye"]
            grammar = "Japanese sentence structure is Subject-Object-Verb. For example: 私はりんごを食べます。"

            self.memory.add_vocab("Japanese", vocab)
            self.memory.mark_lesson_completed("Japanese", "beginner_lesson_1")
            self.memory.increment_streak("Japanese")

            return f"Let's start Japanese! Today's words are: {', '.join(vocab)}\nGrammar tip: {grammar}"
        else:
            return f"{level.title()} Japanese lessons coming soon!"
        
    
    def _teach_mandarin(self, level):
        if level == "beginner":
            vocab = ["你好 - Hello", "谢谢 - Thank you", "再见 - Goodbye"]
            tones = "Mandarin has 4 tones. For example: 妈 (mā), 麻 (má), 马 (mǎ), 骂 (mà)."

            self.memory.add_vocab("Mandarin", vocab)
            self.memory.mark_lesson_completed("Mandarin", "beginner_lesson_1")
            self.memory.increment_streak("Mandarin")

            return f"Let’s start Mandarin! Today's words are: {', '.join(vocab)}\nTone tip: {tones}"
        else:
            return f"{level.title()} Mandarin lessons coming soon!"
        