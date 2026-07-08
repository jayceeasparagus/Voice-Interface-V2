import json
import os
import sys
from collections import Counter

import numpy as np

try:
    from mapping.fixes import apply_text_fixes
    from mapping.text_split import split_text
except ModuleNotFoundError:
    from fixes import apply_text_fixes
    from text_split import split_text


QA_PATH = os.path.join(os.path.dirname(__file__), "qa_pairs.json")
UNKNOWN_ACTION = "unknown"
SIMILARITY_THRESHOLD = 0.35
NGRAM_MIN = 2
NGRAM_MAX = 5


def load_qa_pairs():
    with open(QA_PATH, "r") as file:
        return json.load(file)


def make_embedding(text):
    text = " {} ".format(text.lower().strip())
    counts = Counter()

    for size in range(NGRAM_MIN, NGRAM_MAX + 1):
        for index in range(0, len(text) - size + 1):
            counts[text[index : index + size]] += 1

    return counts


def cosine_similarity(first, second):
    shared_keys = set(first.keys()) & set(second.keys())
    dot = sum(first[key] * second[key] for key in shared_keys)

    first_norm = np.sqrt(sum(value * value for value in first.values()))
    second_norm = np.sqrt(sum(value * value for value in second.values()))

    if first_norm == 0 or second_norm == 0:
        return 0.0

    return float(dot / (first_norm * second_norm))


class SqliteCommandMapper:
    def __init__(self):
        self.qa_pairs = load_qa_pairs()
        self.questions = [item["question"] for item in self.qa_pairs]
        self.actions = [item["command"] for item in self.qa_pairs]
        self.question_embeddings = [make_embedding(question) for question in self.questions]

    def map_action(self, text):
        fixed_text = apply_text_fixes(text)
        text_embedding = make_embedding(fixed_text)

        scores = [
            cosine_similarity(text_embedding, question_embedding)
            for question_embedding in self.question_embeddings
        ]

        if not scores:
            return self.make_result(text, fixed_text, UNKNOWN_ACTION, None, 0.0)

        best_index = int(np.argmax(np.array(scores)))
        best_score = float(scores[best_index])
        best_question = self.questions[best_index]
        best_action = self.actions[best_index]

        if best_score < SIMILARITY_THRESHOLD:
            best_action = UNKNOWN_ACTION

        return self.make_result(
            text,
            fixed_text,
            best_action,
            best_question,
            best_score,
        )

    def make_result(self, text, fixed_text, action, matched_question, score):
        return {
            "input": text,
            "fixed_input": fixed_text,
            "command": action,
            "matched_question": matched_question,
            "score": score,
        }

    def map_text(self, text):
        tasks = split_text(text)
        return [self.map_action(task) for task in tasks]

    def map_commands(self, text):
        return [result["command"] for result in self.map_text(text)]


def main():
    if len(sys.argv) < 2:
        print('Usage: python3 -m mapping.sqlite_mapper "text to map"')
        return

    text = " ".join(sys.argv[1:])
    mapper = SqliteCommandMapper()
    results = mapper.map_text(text)

    print([result["command"] for result in results])
    for result in results:
        print(result)


if __name__ == "__main__":
    main()
