import json
import os
import sqlite3
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
DB_PATH = os.path.join(os.path.dirname(__file__), "qa_pairs.sqlite3")
SIMILARITY_THRESHOLD = 0.35
NGRAM_MIN = 2
NGRAM_MAX = 5


def load_qa_pairs():
    with open(QA_PATH, "r") as file:
        return json.load(file)


def qa_signature(qa_pairs):
    return json.dumps(qa_pairs, sort_keys=True)


def setup_database(qa_pairs):
    db = sqlite3.connect(DB_PATH)
    cur = db.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS qa_pairs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            command TEXT NOT NULL
        )
        """
    )

    cur.execute("SELECT value FROM metadata WHERE key = 'signature'")
    row = cur.fetchone()
    current_signature = qa_signature(qa_pairs)

    if row is None or row[0] != current_signature:
        cur.execute("DELETE FROM qa_pairs")
        for item in qa_pairs:
            cur.execute(
                "INSERT INTO qa_pairs (question, command) VALUES (?, ?)",
                (item["question"], item["command"]),
            )
        cur.execute(
            "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
            ("signature", current_signature),
        )
        db.commit()

    return db


def text_to_ngrams(text):
    text = " {} ".format(text)
    counts = Counter()

    for size in range(NGRAM_MIN, NGRAM_MAX + 1):
        for i in range(0, len(text) - size + 1):
            counts[text[i:i + size]] += 1

    return counts


def cosine_similarity(a_counts, b_counts):
    common_keys = set(a_counts.keys()) & set(b_counts.keys())
    dot = sum(a_counts[key] * b_counts[key] for key in common_keys)

    a_norm = np.sqrt(sum(value * value for value in a_counts.values()))
    b_norm = np.sqrt(sum(value * value for value in b_counts.values()))

    if a_norm == 0 or b_norm == 0:
        return 0.0

    return float(dot / (a_norm * b_norm))


class SqliteCommandMapper:
    def __init__(self):
        self.qa_pairs = load_qa_pairs()
        self.db = setup_database(self.qa_pairs)
        self.questions, self.commands = self.load_pairs_from_db()
        self.question_vectors = [text_to_ngrams(question) for question in self.questions]

    def load_pairs_from_db(self):
        cur = self.db.cursor()
        rows = cur.execute(
            "SELECT question, command FROM qa_pairs ORDER BY id"
        ).fetchall()

        questions = [row[0] for row in rows]
        commands = [row[1] for row in rows]

        return questions, commands

    def map_one(self, text):
        fixed_text = apply_text_fixes(text)
        query_vector = text_to_ngrams(fixed_text)
        scores = [
            cosine_similarity(query_vector, question_vector)
            for question_vector in self.question_vectors
        ]

        if len(scores) == 0:
            return {
                "input": text,
                "fixed_input": fixed_text,
                "command": "unknown",
                "matched_question": None,
                "score": 0.0,
            }

        best_index = int(np.argmax(np.array(scores)))
        best_score = float(scores[best_index])

        if best_score < SIMILARITY_THRESHOLD:
            return {
                "input": text,
                "fixed_input": fixed_text,
                "command": "unknown",
                "matched_question": self.questions[best_index],
                "score": best_score,
            }

        return {
            "input": text,
            "fixed_input": fixed_text,
            "command": self.commands[best_index],
            "matched_question": self.questions[best_index],
            "score": best_score,
        }

    def map_text(self, text):
        results = []

        for task in split_text(text):
            results.append(self.map_one(task))

        return results

    def map_commands(self, text):
        return [result["command"] for result in self.map_text(text)]


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 -m mapping.sqlite_mapper \"command text\"")
        return

    text = " ".join(sys.argv[1:])
    mapper = SqliteCommandMapper()
    print(mapper.map_text(text))


if __name__ == "__main__":
    main()
