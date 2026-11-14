"""Writes dataset.tsv: 50 English prompts + 50 Bangla prompts with the same meaning.

The Bangla was written by hand (no machine translation) and checked pair by pair.
Numbers use Western digits (15, 27) in both languages so only the language differs.
Run:  python3 build_dataset.py
"""
import csv
import os

PAIRS = [
    # ---- question
    ("question", "What is the capital of Bangladesh?", "বাংলাদেশের রাজধানী কী?"),
    ("question", "Who wrote the national anthem of Bangladesh?", "বাংলাদেশের জাতীয় সংগীত কে রচনা করেছেন?"),
    ("question", "How many days are there in a leap year?", "একটি লিপ ইয়ারে (অধিবর্ষে) কত দিন থাকে?"),
    ("question", "What is the name of the longest sea beach in the world, located in Bangladesh?", "বাংলাদেশে অবস্থিত বিশ্বের দীর্ঘতম সমুদ্রসৈকতের নাম কী?"),
    ("question", "Which planet is closest to the Sun?", "সূর্যের সবচেয়ে কাছের গ্রহ কোনটি?"),
    ("question", "What is the chemical formula of water?", "পানির রাসায়নিক সংকেত কী?"),
    ("question", "In which year did Bangladesh become independent?", "বাংলাদেশ কোন সালে স্বাধীন হয়েছিল?"),
    ("question", "What do plants need to make food?", "গাছের খাবার তৈরি করতে কী কী লাগে?"),
    ("question", "Why is the sky blue?", "আকাশ নীল দেখায় কেন?"),
    ("question", "What is the national fruit of Bangladesh?", "বাংলাদেশের জাতীয় ফল কী?"),
    ("question", "How many continents are there in the world?", "পৃথিবীতে কয়টি মহাদেশ আছে?"),
    ("question", "What is the boiling point of water in Celsius?", "সেলসিয়াস স্কেলে পানির স্ফুটনাঙ্ক কত?"),
    # ---- instruction
    ("instruction", "Write a short poem about the rain.", "বৃষ্টি নিয়ে একটি ছোট কবিতা লেখো।"),
    ("instruction", "List three benefits of regular exercise.", "নিয়মিত ব্যায়াম করার তিনটি উপকারিতা লেখো।"),
    ("instruction", "Give me three tips for learning a new language.", "নতুন একটি ভাষা শেখার জন্য তিনটি পরামর্শ দাও।"),
    ("instruction", "Write a polite email asking for a day off.", "একদিনের ছুটি চেয়ে বিনয়ের সাথে একটি ইমেইল লেখো।"),
    ("instruction", "Name five fruits that grow in Bangladesh.", "বাংলাদেশে জন্মায় এমন পাঁচটি ফলের নাম বলো।"),
    ("instruction", "Translate the word \"book\" into French.", "\"বই\" শব্দটিকে ফরাসি ভাষায় অনুবাদ করো।"),
    ("instruction", "Suggest a name for a small tea shop.", "একটি ছোট চায়ের দোকানের জন্য একটি নাম প্রস্তাব করো।"),
    ("instruction", "Write a two-line slogan to encourage people to plant trees.", "মানুষকে গাছ লাগাতে উৎসাহিত করার জন্য দুই লাইনের একটি স্লোগান লেখো।"),
    ("instruction", "Give an example of a healthy breakfast.", "একটি স্বাস্থ্যকর সকালের নাস্তার উদাহরণ দাও।"),
    ("instruction", "Write a greeting for a friend's birthday.", "বন্ধুর জন্মদিনের জন্য একটি শুভেচ্ছা বার্তা লেখো।"),
    # ---- explanation
    ("explanation", "Explain what photosynthesis is in two sentences.", "দুই বাক্যে সালোকসংশ্লেষণ কী তা ব্যাখ্যা করো।"),
    ("explanation", "Briefly explain what the internet is.", "ইন্টারনেট কী তা সংক্ষেপে ব্যাখ্যা করো।"),
    ("explanation", "Explain why we need to drink water every day.", "প্রতিদিন আমাদের কেন পানি পান করা দরকার তা ব্যাখ্যা করো।"),
    ("explanation", "What is the difference between weather and climate?", "আবহাওয়া ও জলবায়ুর মধ্যে পার্থক্য কী?"),
    ("explanation", "Explain what a computer program is in simple words.", "সহজ ভাষায় ব্যাখ্যা করো কম্পিউটার প্রোগ্রাম কী।"),
    ("explanation", "Explain how rain is formed.", "বৃষ্টি কীভাবে হয় তা ব্যাখ্যা করো।"),
    ("explanation", "Briefly describe what a database is.", "ডেটাবেস কী তা সংক্ষেপে বর্ণনা করো।"),
    ("explanation", "Explain why exercise is important for the heart.", "হৃদপিণ্ডের জন্য ব্যায়াম কেন গুরুত্বপূর্ণ তা ব্যাখ্যা করো।"),
    # ---- arithmetic
    ("arithmetic", "What is 15 plus 27?", "15 এর সাথে 27 যোগ করলে কত হয়?"),
    ("arithmetic", "What is 144 divided by 12?", "144 কে 12 দিয়ে ভাগ করলে কত হয়?"),
    ("arithmetic", "What is 25 multiplied by 4?", "25 কে 4 দিয়ে গুণ করলে কত হয়?"),
    ("arithmetic", "If a pen costs 12 taka, how much do 7 pens cost?", "একটি কলমের দাম 12 টাকা হলে 7টি কলমের দাম কত?"),
    ("arithmetic", "What is 20 percent of 150?", "150 এর 20 শতাংশ কত?"),
    ("arithmetic", "A train travels 60 kilometres in one hour. How far does it travel in 3 hours?", "একটি ট্রেন এক ঘণ্টায় 60 কিলোমিটার যায়। 3 ঘণ্টায় ট্রেনটি কত দূর যাবে?"),
    ("arithmetic", "What is the square of 13?", "13 এর বর্গ কত?"),
    ("arithmetic", "Rahim has 50 taka and spends 18 taka. How much money is left?", "রহিমের কাছে 50 টাকা আছে। সে 18 টাকা খরচ করলে তার কাছে কত টাকা থাকবে?"),
    # ---- summarise
    ("summarise", "Summarise this sentence in a few words: \"The library will be closed on Friday because of maintenance work, and it will reopen on Saturday morning.\"", "এই বাক্যটি কয়েকটি শব্দে সংক্ষেপ করো: \"মেরামতের কাজের জন্য শুক্রবার লাইব্রেরি বন্ধ থাকবে এবং শনিবার সকালে আবার খুলবে।\""),
    ("summarise", "Summarise in one short sentence: \"Regular sleep helps the body recover, improves memory, and keeps the mind calm during the day.\"", "এক ছোট বাক্যে সংক্ষেপ করো: \"নিয়মিত ঘুম শরীরকে সেরে উঠতে সাহায্য করে, স্মৃতিশক্তি বাড়ায় এবং দিনের বেলায় মনকে শান্ত রাখে।\""),
    ("summarise", "Summarise: \"The farmers planted rice in June, and after heavy rain in July, the fields were full of water, but the harvest in November was still good.\"", "সংক্ষেপ করো: \"কৃষকেরা জুন মাসে ধান লাগিয়েছিলেন, জুলাই মাসে ভারী বৃষ্টির পর মাঠ পানিতে ভরে গিয়েছিল, তবুও নভেম্বর মাসে ফসল ভালো হয়েছিল।\""),
    ("summarise", "Give the main idea of this sentence: \"Public parks give city dwellers a place to rest, play, and meet their neighbours.\"", "এই বাক্যটির মূল ভাব বলো: \"পাবলিক পার্ক শহরের মানুষকে বিশ্রাম নেওয়ার, খেলার এবং প্রতিবেশীদের সাথে দেখা করার জায়গা দেয়।\""),
    ("summarise", "Summarise in a few words: \"The new bus service connects the village to the town every hour, so students can reach school on time.\"", "কয়েকটি শব্দে সংক্ষেপ করো: \"নতুন বাস সার্ভিস প্রতি ঘণ্টায় গ্রাম ও শহরের মধ্যে চলাচল করে, তাই শিক্ষার্থীরা সময়মতো স্কুলে পৌঁছাতে পারে।\""),
    ("summarise", "Summarise: \"Mangoes ripen in summer, and families often share them with neighbours because the trees give more fruit than one house can eat.\"", "সংক্ষেপ করো: \"আম গ্রীষ্মকালে পাকে এবং পরিবারগুলো প্রায়ই প্রতিবেশীদের সাথে তা ভাগ করে নেয়, কারণ গাছে একটি বাড়ির খাওয়ার চেয়ে বেশি ফল ধরে।\""),
    # ---- long
    ("long", "I am planning a small birthday party for my younger sister next week. She likes chocolate cake and loves drawing. Suggest a simple plan for the party, including food, one activity, and a decoration idea. Keep the suggestions cheap because our budget is small.", "আমি আগামী সপ্তাহে আমার ছোট বোনের জন্য একটি ঘরোয়া জন্মদিনের অনুষ্ঠানের পরিকল্পনা করছি। সে চকলেট কেক পছন্দ করে এবং ছবি আঁকতে ভালোবাসে। খাবার, একটি কার্যক্রম এবং একটি সাজসজ্জার ধারণাসহ অনুষ্ঠানের জন্য একটি সহজ পরিকল্পনা প্রস্তাব করো। আমাদের বাজেট কম, তাই পরামর্শগুলো কম খরচের হতে হবে।"),
    ("long", "My phone battery drains very quickly, even when I am not using it. I have already closed most of the apps and lowered the screen brightness. The phone is about two years old. What could be the reasons, and what should I check first?", "আমার ফোনের ব্যাটারির চার্জ খুব দ্রুত শেষ হয়ে যায়, এমনকি ফোনটি ব্যবহার না করলেও। আমি ইতিমধ্যে বেশিরভাগ অ্যাপ বন্ধ করেছি এবং স্ক্রিনের উজ্জ্বলতা কমিয়েছি। ফোনটি প্রায় দুই বছরের পুরোনো। এর কারণ কী হতে পারে, আর আমার প্রথমে কী পরীক্ষা করা উচিত?"),
    ("long", "I want to start learning programming, but I have never written any code before. I can study for one hour every day after school. Which language should I start with, and how should I organise my first month? Give simple steps.", "আমি প্রোগ্রামিং শেখা শুরু করতে চাই, কিন্তু আগে কখনো কোনো কোড লিখিনি। স্কুলের পর আমি প্রতিদিন এক ঘণ্টা পড়ার সময় পাই। আমার কোন প্রোগ্রামিং ভাষা দিয়ে শুরু করা উচিত, আর প্রথম এক মাসের পড়াশোনা কীভাবে সাজাব? সহজ ধাপে বলো।"),
    ("long", "Our neighbourhood has a lot of plastic waste on the street after the weekly market. Many shopkeepers say they do not have time to clean it. Write a short message to the shopkeepers that asks them to help, in a friendly tone.", "সাপ্তাহিক বাজারের পর আমাদের পাড়ার রাস্তায় অনেক প্লাস্টিক বর্জ্য পড়ে থাকে। অনেক দোকানদার বলেন, পরিষ্কার করার মতো সময় তাঁদের নেই। দোকানদারদের উদ্দেশে বন্ধুত্বপূর্ণ সুরে একটি ছোট বার্তা লেখো, যাতে তাঁদের সাহায্য করতে অনুরোধ করা হয়।"),
    ("long", "A student scored 70 in mathematics, 85 in science, and 90 in English. The teacher says the average score decides the final grade. Calculate the average score of the student, and then say whether it is above 80. Show the steps briefly.", "একজন শিক্ষার্থী গণিতে 70, বিজ্ঞানে 85 এবং ইংরেজিতে 90 পেয়েছে। শিক্ষক বলেছেন, গড় নম্বর দিয়ে চূড়ান্ত গ্রেড ঠিক হবে। শিক্ষার্থীর গড় নম্বর হিসাব করো, তারপর বলো গড়টি 80 এর বেশি কি না। ধাপগুলো সংক্ষেপে দেখাও।"),
    ("long", "Many people say that reading books before sleep helps them relax. Others prefer to watch videos on their phones. Compare the two habits in a few sentences. Say which one is better for sleep and give one reason.", "অনেকে বলেন ঘুমানোর আগে বই পড়লে মন শান্ত হয়। অন্যরা ফোনে ভিডিও দেখতে পছন্দ করেন। কয়েকটি বাক্যে এই দুটি অভ্যাসের তুলনা করো। ঘুমের জন্য কোনটি ভালো তা বলো এবং একটি কারণ দাও।"),
]


def main():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dataset.tsv")
    with open(path, "w", encoding="utf-8-sig", newline="") as f:  # BOM so Excel shows Bangla correctly
        w = csv.writer(f, delimiter="\t", quoting=csv.QUOTE_MINIMAL)
        w.writerow(["id", "category", "english", "bangla"])
        for i, (cat, en, bn) in enumerate(PAIRS, 1):
            w.writerow([i, cat, en, bn])
    print(f"wrote {len(PAIRS)} pairs to {path}")


if __name__ == "__main__":
    main()
