from gost_video_signer import GOSTVideoSteganographer


# Инициализация
signer = GOSTVideoSteganographer()

# Генерация ключей
print("🔐 Генерация ключей...")
private_key, public_key = signer.generate_keys()

# Сохраняем открытый и закрытый ключи
with open("keys\public_key.bin", "wb") as f:
    f.write(public_key)

with open("keys\private_key.bin", "wb") as f:
    f.write(private_key)