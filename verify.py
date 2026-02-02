from gost_video_signer import GOSTVideoSteganographer
import os


class VideoVerifier:
    """Класс для удобной проверки видео"""
    
    def __init__(self, public_key_path=None):
        self.signer = GOSTVideoSteganographer()
        
        if public_key_path and os.path.exists(public_key_path):
            self.load_public_key(public_key_path)
    
    def load_public_key(self, public_key_path):
        """Загрузка публичного ключа из файла"""
        try:
            with open(public_key_path, "rb") as f:
                self.signer.public_key = f.read()
            print(f"✅ Публичный ключ загружен: {public_key_path}")
            return True
        except Exception as e:
            print(f"❌ Ошибка загрузки ключа: {e}")
            return False
    
    def verify_video(self, video_path):
        """Проверка целостности видео"""
        if self.signer.public_key is None:
            print("❌ Ошибка: Публичный ключ не установлен!")
            return False
        
        print(f"🔍 Проверка видео: {os.path.basename(video_path)}")
        
        try:
            is_authentic = self.signer.verify_watermarked_video_self_contained(video_path)
            
            if is_authentic:
                print("\n✅ ВИДЕО ПОДЛИННОЕ!")
                print("   ✓ Цифровая подпись подтверждена")
                print("   ✓ Видео не изменялось после подписания")
                print("   ✓ Целостность данных сохранена")
            else:
                print("\n❌ ВНИМАНИЕ! Видео не прошло проверку")
                print("   ✗ Видео было изменено или повреждено")
            
            return is_authentic
            
        except Exception as e:
            print(f"❌ Ошибка при проверке: {e}")
            return False

if __name__ == "__main__":
    # Использование

    # Создаем получателя с нужным ключом
    verifier = VideoVerifier("keys\public_key.bin")

    # Проверяем
    is_valid = verifier.verify_video("video_signed.h264")