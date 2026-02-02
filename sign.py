from gost_video_signer import GOSTVideoSteganographer
import os
import secrets

class VideoSender:
    """Класс для отправителя видео с поддержкой пользовательских ключей"""
    
    def __init__(self, private_key=None, public_key=None):
        """
        Инициализация отправителя
        
        Args:
            private_key: Приватный ключ (bytes или hex строка)
            public_key: Публичный ключ (bytes или hex строка)
        """
        self.signer = GOSTVideoSteganographer()
        
        if private_key is not None and public_key is not None:
            self.set_keys(private_key, public_key)
    
    def set_keys(self, private_key, public_key):
        """Установка пользовательских ключей"""
        # Конвертируем из hex строки если нужно
        if isinstance(private_key, str):
            private_key = bytes.fromhex(private_key)
        if isinstance(public_key, str):
            public_key = bytes.fromhex(public_key)
        
        self.signer.private_key = private_key
        self.signer.public_key = public_key
        
        print("✅ Пользовательские ключи установлены")
        print(f"   Приватный ключ: {private_key.hex()[:32]}...")
        print(f"   Публичный ключ: {public_key.hex()[:32]}...")
    
    def generate_keys(self):
        """Генерация новых ключей (альтернатива пользовательским)"""
        private_key, public_key = self.signer.generate_keys()
        print("✅ Новые ключи сгенерированы")
        return private_key, public_key
    
    def save_keys(self, private_key_path="private_key.bin", public_key_path="public_key.bin"):
        """Сохранение ключей в файлы"""
        if self.signer.private_key is None or self.signer.public_key is None:
            print("❌ Ключи не установлены")
            return False
        
        try:
            with open(private_key_path, "wb") as f:
                f.write(self.signer.private_key)
            with open(public_key_path, "wb") as f:
                f.write(self.signer.public_key)
            
            print(f"✅ Ключи сохранены:")
            print(f"   Приватный ключ: {private_key_path}")
            print(f"   Публичный ключ: {public_key_path}")
            return True
        except Exception as e:
            print(f"❌ Ошибка сохранения ключей: {e}")
            return False
    
    def load_keys_from_files(self, private_key_path="private_key.bin", public_key_path="public_key.bin"):
        """Загрузка ключей из файлов"""
        try:
            with open(private_key_path, "rb") as f:
                private_key = f.read()
            with open(public_key_path, "rb") as f:
                public_key = f.read()
            
            self.set_keys(private_key, public_key)
            print(f"✅ Ключи загружены из файлов")
            return True
        except Exception as e:
            print(f"❌ Ошибка загрузки ключей: {e}")
            return False
    
    def sign_and_watermark_video(self, input_video_path, output_video_path=None):
        """Подписание видео и внедрение ЦВЗ"""
        if self.signer.private_key is None:
            print("❌ Ошибка: Приватный ключ не установлен")
            return None
        
        print(f"🎬 Обработка видео: {os.path.basename(input_video_path)}")
        
        try:
            # Подписываем видео
            signature, video_hash = self.signer.sign_video(input_video_path)
            
            # Создаем подписанную версию
            if output_video_path is None:
                base_name = os.path.splitext(input_video_path)[0]
                output_video_path = f"{base_name}_signed.h264"
            
            watermarked_path = self.signer.embed_signature_as_watermark(
                input_video_path, signature, output_video_path
            )
            
            print(f"✅ Видео успешно подписано: {watermarked_path}")
            print(f"📊 Хеш видео: {video_hash.hex()}")
            print(f"📏 Размер подписи: {len(signature)} байт")
            
            return watermarked_path, signature
            
        except Exception as e:
            print(f"❌ Ошибка при подписании видео: {e}")
            return None
    
    def get_key_info(self):
        """Получение информации о ключах"""
        if self.signer.private_key is None or self.signer.public_key is None:
            return "Ключи не установлены"
        
        return {
            "private_key_length": len(self.signer.private_key),
            "public_key_length": len(self.signer.public_key),
            "private_key_hex": self.signer.private_key.hex(),
            "public_key_hex": self.signer.public_key.hex()
        }


if __name__ == "__main__":
    # Использование
    
    # Создаем отправителя
    sender = VideoSender()
    
    # Загружаем ключи из файлов
    if sender.load_keys_from_files("keys\private_key.bin", "keys\public_key.bin"):
        # Подписываем видео
        video_path = "video.h264"
        result = sender.sign_and_watermark_video(video_path)
        
        if result:
            signed_video, signature = result
            print(f"✅ Видео подписано: {signed_video}")
