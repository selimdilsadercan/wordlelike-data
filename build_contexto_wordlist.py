import random

IN_FILE = "words.txt"              # ham TDK sözlüğün
OUT_FILE = "words_contexto.txt"    # çıkacak temiz liste
TARGET_TOTAL = 15000               # 10-15k arası istiyorsan burayı oynatabilirsin

TR_CHARS = set("abcçdefgğhıijklmnoöprsştuüvyz")
VOWELS = set("aeıioöuü")

def is_good(raw: str) -> bool:
    raw = raw.strip()
    if not raw:
        return False

    # boşluk, noktalama, rakam, özel işaret
    if any(ch.isspace() for ch in raw):
        return False
    if any(ch in "-_./,;:!?\"'()[]{}+*=<>”’" for ch in raw):
        return False
    if any(ch.isdigit() for ch in raw):
        return False

    # büyük harfle başlıyorsa muhtemelen özel isim
    if raw[0].isupper():
        return False

    w = raw.lower()

    # uzunluk
    if len(w) < 3 or len(w) > 15:
        return False

    # sadece Türkçe harfler
    if any(ch not in TR_CHARS for ch in w):
        return False

    # en az bir sesli harf olsun (kısaltmaları at)
    if not any(ch in VOWELS for ch in w):
        return False

    # normalize edilmiş hali ile aynı olsun
    if w != raw:
        return False

    return True


def main():
    print("Ham kelimeler okunuyor...")
    words = []
    with open(IN_FILE, "r", encoding="utf-8") as f:
        for line in f:
            raw = line.strip()
            if not raw:
                continue
            if is_good(raw):
                words.append(raw.lower())

    # uniq yap
    words = sorted(set(words))
    print(f"Filtre sonrası toplam {len(words)} kelime kaldı.")

    # kısa / uzun diye ayır
    short = [w for w in words if len(w) <= 6]
    long = [w for w in words if len(w) > 6]

    print(f"Kısa (<=6 harf) kelime sayısı: {len(short)}")
    print(f"Uzun   (>6 harf) kelime sayısı: {len(long)}")

    # hedefe göre uzunlardan ne kadar almamız gerektiğini hesapla
    needed = max(0, TARGET_TOTAL - len(short))
    if needed > len(long):
        needed = len(long)

    random.seed(42)  # deterministik olsun
    long_sample = random.sample(long, needed)

    final_words = sorted(set(short) | set(long_sample))
    print(f"Nihai Contexto listesi: {len(final_words)} kelime.")

    with open(OUT_FILE, "w", encoding="utf-8") as out:
        for w in final_words:
            out.write(w + "\n")

    print(f"'{OUT_FILE}' dosyasına yazıldı.")


if __name__ == "__main__":
    main()
