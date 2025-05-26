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
            grammar = "Japanese sentence structure is Subject-Object-Verb. E.g., 私はりんごを食べます。"
            lesson_id = "beginner_lesson_1"

        elif level == "intermediate":
            vocab = ["勉強する - To study", "図書館 - Library", "宿題 - Homework"]
            grammar = "Use of ~ている for ongoing actions: 勉強しています means 'is studying'."
            lesson_id = "intermediate_lesson_1"

        elif level == "advanced":
            vocab = ["仮定 - Hypothesis", "逆説 - Paradox", "抽象的 - Abstract"]
            grammar = "Advanced sentence connectors like にもかかわらず (despite), ながらも (although)."
            lesson_id = "advanced_lesson_1"

        else:
            return f"{level.title()} Japanese lessons coming soon!"

        self.memory.add_vocab("Japanese", vocab)
        self.memory.mark_lesson_completed("Japanese", lesson_id)
        self.memory.increment_streak("Japanese")

        return f"Let's start {level} Japanese! Today's words: {', '.join(vocab)}\nGrammar tip: {grammar}"

    def _teach_mandarin(self, level):
        if level == "beginner":
            vocab = ["你好 - Hello", "谢谢 - Thank you", "再见 - Goodbye"]
            grammar = "Mandarin has 4 tones. E.g., 妈 (mā), 麻 (má), 马 (mǎ), 骂 (mà)."
            lesson_id = "beginner_lesson_1"

        elif level == "intermediate":
            vocab = ["图书馆 - Library", "学习 - Study", "作业 - Homework"]
            grammar = "Basic word order: Subject-Verb-Object. 他在图书馆学习。 (He studies in the library.)"
            lesson_id = "intermediate_lesson_1"

        elif level == "advanced":
            vocab = ["抽象 - Abstract", "假设 - Hypothesis", "悖论 - Paradox"]
            grammar = "Advanced patterns: 虽然...但是 (Although...), 尽管...还是 (Even though...)"
            lesson_id = "advanced_lesson_1"

        else:
            return f"{level.title()} Mandarin lessons coming soon!"

        self.memory.add_vocab("Mandarin", vocab)
        self.memory.mark_lesson_completed("Mandarin", lesson_id)
        self.memory.increment_streak("Mandarin")

        return f"Let's start {level} Mandarin! Today's words: {', '.join(vocab)}\nGrammar tip: {grammar}"
