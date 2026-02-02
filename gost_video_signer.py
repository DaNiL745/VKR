import secrets
import os
from gostcrypto import gostsignature
from gostcrypto import gosthash

class GOSTVideoSteganographer:
    def __init__(self):
        self.private_key = None
        self.public_key = None
        self.sign_obj = None
        self._initialize_signer()
        
    def _initialize_signer(self):
        """Инициализация объекта для подписи"""
        try:
            self.sign_obj = gostsignature.new(
                gostsignature.MODE_256,
                gostsignature.CURVES_R_1323565_1_024_2019['id-tc26-gost-3410-2012-256-paramSetA']
            )
        except Exception as e:
            print(f"⚠️ Предупреждение: не удалось инициализировать подписыватель: {e}")
            self.sign_obj = None
    
    def generate_keys(self):
        """Генерация пары ключей"""
        if self.sign_obj is None:
            self._initialize_signer()
            if self.sign_obj is None:
                raise ValueError("Не удалось инициализировать подписыватель")
        
        self.private_key = secrets.token_bytes(32)
        self.public_key = self.sign_obj.public_key_generate(self.private_key)
        
        return self.private_key, self.public_key
    
    def set_public_key(self, public_key):
        """Установка публичного ключа для проверки"""
        self.public_key = public_key
        if self.sign_obj is None:
            self._initialize_signer()
    
    def load_public_key_from_file(self, public_key_path):
        """Загрузка публичного ключа из файла"""
        try:
            with open(public_key_path, "rb") as f:
                self.public_key = f.read()
            print(f"✅ Публичный ключ загружен: {public_key_path}")
            
            # Инициализируем подписыватель если нужно
            if self.sign_obj is None:
                self._initialize_signer()
                
            return True
        except Exception as e:
            print(f"❌ Ошибка загрузки ключа: {e}")
            return False

    def hash_video_file(self, file_path, chunk_size=8192):
        """Вычисление хеша видеофайла с прогресс-баром"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Файл не найден: {file_path}")
        
        file_size = os.path.getsize(file_path)
        hash_obj = gosthash.new('streebog256')
        
        print(f"Хеширование файла: {os.path.basename(file_path)}")
        print(f"Размер файла: {file_size} байт")
        
        with open(file_path, 'rb') as f:
            bytes_processed = 0
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                hash_obj.update(chunk)
                bytes_processed += len(chunk)
                
                progress = (bytes_processed / file_size) * 100
                print(f"\rПрогресс: {progress:.1f}% [{bytes_processed}/{file_size} байт]", end='', flush=True)
        
        print("\nХеширование завершено!")
        return hash_obj.digest()
    
    def sign_video(self, file_path):
        """Подписание видеофайла"""
        if self.sign_obj is None or self.private_key is None:
            raise ValueError("Сначала сгенерируйте ключи")
            
        print(f"Подписание видеофайла: {file_path}")
        
        video_hash = self.hash_video_file(file_path)
        print(f"Хеш видео: {video_hash.hex()}")
        
        signature = self.sign_obj.sign(self.private_key, video_hash)
        print(f"Подпись создана, длина: {len(signature)} байт")
        
        return signature, video_hash
    
    def embed_signature_as_watermark(self, input_video_path, signature, output_video_path=None):
        """Внедрение подписи как ЦВЗ в H.264 видео"""
        if output_video_path is None:
            base_name = os.path.splitext(input_video_path)[0]
            output_video_path = f"{base_name}_watermarked.h264"
        
        print(f"Внедрение ЦВЗ в видео: {input_video_path}")
        print(f"Выходной файл: {output_video_path}")
        
        try:
            with open(input_video_path, 'rb') as f_in:
                original_data = f_in.read()
            
            # Внедряем подпись в SEI сообщения
            watermarked_data = self._embed_in_sei_messages(original_data, signature)
            
            with open(output_video_path, 'wb') as f_out:
                f_out.write(watermarked_data)
            
            print(f"ЦВЗ успешно внедрен в: {output_video_path}")
            
            # Проверим, что файл создан
            if os.path.exists(output_video_path):
                output_size = os.path.getsize(output_video_path)
                input_size = len(original_data)
                print(f"Размер исходного файла: {input_size} байт")
                print(f"Размер файла с ЦВЗ: {output_size} байт")
                print(f"Разница: {output_size - input_size} байт")
            
            return output_video_path
            
        except Exception as e:
            print(f"Ошибка при внедрении ЦВЗ: {e}")
            return None
    
    def _embed_in_sei_messages(self, video_data, signature):
        """Внедрение подписи в SEI сообщения"""
        print("Создание SEI сообщения с подписью...")
        
        # Создаем пользовательское SEI сообщение с подписью
        sei_payload = self._create_sei_payload(signature)
        print(f"Длина SEI сообщения: {len(sei_payload)} байт")
        
        # Ищем хорошее место для вставки SEI сообщения
        insertion_point = self._find_best_insertion_point(video_data)
        print(f"Точка вставки: {insertion_point}")
        
        if insertion_point == -1:
            print("Не найдена подходящая точка вставки, вставляем в начало")
            insertion_point = 0
        
        # Вставляем SEI сообщение
        watermarked_data = (video_data[:insertion_point] + 
                           sei_payload + 
                           video_data[insertion_point:])
        
        print("SEI сообщение успешно вставлено")
        return watermarked_data
    
    def _create_sei_payload(self, signature):
        """Создание SEI payload с подписью"""
        # UUID для идентификации нашего ЦВЗ
        uuid = b'GOST_SIGNATURE_V1'
        
        # Собираем данные payload
        payload_data = uuid + signature
        
        # SEI NAL unit structure
        sei_nal_unit = bytearray()
        
        # Start code
        sei_nal_unit.extend(b'\x00\x00\x00\x01')
        
        # NAL header (6 - SEI message, nal_ref_idc=0)
        sei_nal_unit.append(0x06)
        
        # Payload type (5 - user_data_unregistered)
        sei_nal_unit.append(0x05)
        
        # Payload size (в унарном кодировании)
        payload_size = len(payload_data)
        while payload_size >= 255:
            sei_nal_unit.append(0xFF)
            payload_size -= 255
        sei_nal_unit.append(payload_size)
        
        # Payload data
        sei_nal_unit.extend(payload_data)
        
        # RBSP trailing bits
        sei_nal_unit.append(0x80)
        
        return bytes(sei_nal_unit)
    
    def _find_best_insertion_point(self, video_data):
        """Поиск лучшей точки для вставки SEI сообщения"""
        print("Поиск точки для вставки SEI сообщения...")
        
        # Ищем последовательность параметров (SPS/PPS)
        i = 0
        sps_found = False
        pps_found = False
        
        while i < len(video_data) - 8:
            # Ищем start code
            if (video_data[i] == 0x00 and video_data[i+1] == 0x00 and 
                video_data[i+2] == 0x00 and video_data[i+3] == 0x01):
                
                nal_unit_type = video_data[i+4] & 0x1F
                
                if nal_unit_type == 7:  # SPS
                    print("Найден SPS NAL unit")
                    sps_found = True
                elif nal_unit_type == 8:  # PPS
                    print("Найден PPS NAL unit")
                    pps_found = True
                elif nal_unit_type == 1 and sps_found and pps_found:  # Slice of IDR picture
                    print("Найден IDR slice - идеальное место для вставки")
                    return i  # Вставляем перед первым IDR кадром
                elif nal_unit_type == 6:  # SEI
                    print("Найдено существующее SEI сообщение")
                    # Можно вставить после существующего SEI
                    next_start = self._find_next_start_code(video_data, i + 4)
                    if next_start != -1:
                        return next_start
                
                # Переходим к следующему NAL unit
                next_start = self._find_next_start_code(video_data, i + 4)
                if next_start == -1:
                    break
                i = next_start
            else:
                i += 1
        
        # Если не нашли идеальное место, вставляем после первых SPS/PPS
        if sps_found and pps_found:
            print("Вставляем после SPS/PPS последовательности")
            return self._find_position_after_sps_pps(video_data)
        
        # Последний вариант - вставляем в начало
        print("Вставляем в начало файла")
        return 0
    
    def _find_next_start_code(self, data, start_pos):
        """Поиск следующего start code"""
        i = start_pos
        while i < len(data) - 4:
            if (data[i] == 0x00 and data[i+1] == 0x00 and 
                data[i+2] == 0x00 and data[i+3] == 0x01):
                return i
            i += 1
        return -1
    
    def _find_position_after_sps_pps(self, video_data):
        """Поиск позиции после SPS/PPS последовательности"""
        i = 0
        last_sps_pps_pos = 0
        
        while i < len(video_data) - 8:
            if (video_data[i] == 0x00 and video_data[i+1] == 0x00 and 
                video_data[i+2] == 0x00 and video_data[i+3] == 0x01):
                
                nal_unit_type = video_data[i+4] & 0x1F
                
                if nal_unit_type == 7 or nal_unit_type == 8:  # SPS или PPS
                    last_sps_pps_pos = i
                    # Ищем следующий start code после этого NAL unit
                    next_start = self._find_next_start_code(video_data, i + 4)
                    if next_start != -1:
                        nal_unit_type_next = video_data[next_start + 4] & 0x1F
                        if nal_unit_type_next != 7 and nal_unit_type_next != 8:
                            return next_start  # Возвращаем позицию перед следующим не-SPS/PPS NAL unit
                
                i += 4
            else:
                i += 1
        
        return last_sps_pps_pos + 100
    
    def extract_signature_and_restore_video(self, watermarked_video_path, output_restored_path=None):
        """Извлечение подписи и восстановление оригинального видео"""
        print(f"Извлечение ЦВЗ и восстановление видео: {watermarked_video_path}")
        
        try:
            with open(watermarked_video_path, 'rb') as f:
                watermarked_data = f.read()
            
            print(f"Размер файла для анализа: {len(watermarked_data)} байт")
            
            # Извлекаем подпись и получаем восстановленные данные
            signature, restored_data = self._extract_signature_and_remove_watermark(watermarked_data)
            
            if signature and restored_data:
                print(f"Подпись извлечена, длина: {len(signature)} байт")
                
                # Сохраняем восстановленное видео
                if output_restored_path is None:
                    base_name = os.path.splitext(watermarked_video_path)[0]
                    output_restored_path = f"{base_name}_restored.h264"
                
                with open(output_restored_path, 'wb') as f:
                    f.write(restored_data)
                
                restored_size = len(restored_data)
                print(f"Восстановленное видео сохранено: {output_restored_path}")
                print(f"Размер восстановленного файла: {restored_size} байт")
                
                return signature, output_restored_path
            else:
                print("Не удалось извлечь подпись и восстановить видео")
                return None, None
                
        except Exception as e:
            print(f"Ошибка при извлечении и восстановлении: {e}")
            return None, None
    
    def _extract_signature_and_remove_watermark(self, watermarked_data):
        """Извлечение подписи и удаление водяного знака"""
        print("Поиск и удаление SEI сообщения с подписью...")
        
        i = 0
        
        while i < len(watermarked_data) - 20:
            # Ищем start code
            if (watermarked_data[i] == 0x00 and 
                watermarked_data[i+1] == 0x00 and 
                watermarked_data[i+2] == 0x00 and 
                watermarked_data[i+3] == 0x01):
                
                nal_unit_type = watermarked_data[i+4] & 0x1F
                
                if nal_unit_type == 6:  # SEI message
                    print(f"Найдено SEI сообщение на позиции {i}")
                    
                    # Парсим SEI для извлечения подписи и определения длины
                    signature, sei_length = self._parse_sei_and_get_length(watermarked_data, i)
                    
                    if signature and sei_length > 0:
                        print("Подпись извлечена из SEI сообщения")
                        
                        # Удаляем SEI сообщение из данных
                        start_pos = i
                        end_pos = i + sei_length
                        
                        # Создаем восстановленные данные
                        restored_data = watermarked_data[:start_pos] + watermarked_data[end_pos:]
                        
                        print(f"SEI сообщение удалено (длина: {sei_length} байт)")
                        print(f"Восстановлено {len(restored_data)} байт")
                        
                        return signature, restored_data
                    else:
                        print("Не удалось извлечь подпись или определить длину SEI")
                
                # Переходим к следующему NAL unit
                next_start = self._find_next_start_code(watermarked_data, i + 4)
                if next_start == -1:
                    break
                i = next_start
            else:
                i += 1
        
        print("SEI сообщение с подписью не найдено")
        return None, None
    
    def _parse_sei_and_get_length(self, video_data, start_pos):
        """Парсинг SEI payload и извлечение подписи с определением полной длины SEI NAL unit"""
        pos = start_pos + 4  # Пропускаем start code, теперь на nal_header
        
        if pos >= len(video_data):
            return None, 0
        
        nal_header = video_data[pos]
        pos += 1
        
        # Читаем payload type
        payload_type = 0
        while pos < len(video_data) and video_data[pos] == 0xFF:
            payload_type += 0xFF
            pos += 1
        if pos < len(video_data):
            payload_type += video_data[pos]
            pos += 1
        else:
            return None, 0
        
        # Читаем payload size
        payload_size = 0
        while pos < len(video_data) and video_data[pos] == 0xFF:
            payload_size += 0xFF
            pos += 1
        if pos < len(video_data):
            payload_size += video_data[pos]
            pos += 1
        else:
            return None, 0
        
        print(f"SEI payload type: {payload_type}, size: {payload_size}")
        
        # Проверяем, что это наш payload (user_data_unregistered = 5)
        if payload_type == 5 and pos + payload_size <= len(video_data):
            payload_data = video_data[pos:pos + payload_size]
            
            # Проверяем наш UUID
            uuid = b'GOST_SIGNATURE_V1'
            if payload_data[:len(uuid)] == uuid:
                print("Найден наш UUID в SEI сообщении")
                # Извлекаем подпись (все что после UUID)
                signature = payload_data[len(uuid):]
                if len(signature) == 64:  # Ожидаемая длина подписи ГОСТ
                    # Вычисляем полную длину SEI NAL unit
                    # start_code(4) + nal_header(1) + payload_type_bytes + payload_size_bytes + payload_data + trailing_bit(1)
                    
                    # Подсчитываем байты, потраченные на кодирование payload_type
                    payload_type_bytes = 1
                    temp_type = payload_type
                    while temp_type >= 255:
                        payload_type_bytes += 1
                        temp_type -= 255
                    
                    # Подсчитываем байты, потраченные на кодирование payload_size  
                    payload_size_bytes = 1
                    temp_size = payload_size
                    while temp_size >= 255:
                        payload_size_bytes += 1
                        temp_size -= 255
                    
                    # Полная длина SEI NAL unit
                    sei_length = 4 + 1 + payload_type_bytes + payload_size_bytes + payload_size + 1
                    
                    print(f"Полная длина SEI: {sei_length} байт")
                    return signature, sei_length
        
        return None, 0
    
    def verify_watermarked_video_self_contained(self, watermarked_video_path):
        """Проверка целостности подписанное видео без оригинала"""
        print("Проверка целостности подписанное видео (самостоятельная проверка)...")
        
        # Шаг 1: Извлекаем подпись и восстанавливаем видео
        signature, restored_video_path = self.extract_signature_and_restore_video(watermarked_video_path)
        
        if not signature or not restored_video_path:
            print("❌ Не удалось извлечь подпись или восстановить видео")
            return False
        
        # Шаг 2: Проверяем подпись на восстановленном видео
        print("Проверка подписи на восстановленном видео...")
        is_valid = self.verify_video(restored_video_path, signature)
        
        # Шаг 3: Проверяем размер восстановленного файла
        original_size = os.path.getsize(watermarked_video_path) - len(signature) - 16 - 11  # Подпись + UUID + накладные расходы
        restored_size = os.path.getsize(restored_video_path)
        
        print(f"Ожидаемый размер: {original_size} байт")
        print(f"Фактический размер: {restored_size} байт")
        
        if is_valid:
            print("✅ Видео прошло самостоятельную проверку целостности!")
            print("   - Подпись успешно извлечена из ЦВЗ")
            print("   - Видео успешно восстановлено") 
            print("   - Подпись валидна для восстановленного видео")
        else:
            print("❌ Видео не прошло проверку целостности!")
            print("   - Возможно видео было изменено после подписания")
        
        # Очистка временного файла
        if os.path.exists(restored_video_path):
            os.remove(restored_video_path)
            print(f"Временный файл удален: {restored_video_path}")
        
        return is_valid
    
    def verify_video(self, file_path, signature):
        """Проверка подписи видеофайла"""
        if self.sign_obj is None or self.public_key is None:
            raise ValueError("Открытый ключ не установлен")
            
        print(f"Проверка подписи видеофайла: {file_path}")
        
        video_hash = self.hash_video_file(file_path)
        print(f"Вычисленный хеш видео: {video_hash.hex()}")
        
        try:
            result = self.sign_obj.verify(self.public_key, video_hash, signature)
            return result
        except Exception as e:
            print(f"Ошибка при проверке подписи: {e}")
            return False

def simple_demo():
    """Простая демонстрация работы"""
    print("=== ПРОСТАЯ ДЕМОНСТРАЦИЯ РАБОТЫ ===")
    
    # Создаем подписыватель
    signer = GOSTVideoSteganographer()
    signer.generate_keys()
    
    # Используем тестовое видео
    video_path = "video.h264"
    
    if not os.path.exists(video_path):
        print(f"Файл {video_path} не найден!")
        return
    
    print("\n1. Подписание видео...")
    signature, original_hash = signer.sign_video(video_path)
    print(f"   Оригинальный хеш: {original_hash.hex()}")
    
    print("\n2. Внедрение ЦВЗ...")
    watermarked_path = signer.embed_signature_as_watermark(video_path, signature)
    
    print("\n3. Проверка целостности БЕЗ оригинала...")
    is_valid = signer.verify_watermarked_video_self_contained(watermarked_path)
    
    print(f"\n🎯 РЕЗУЛЬТАТ: {'✅ УСПЕХ' if is_valid else '❌ ОШИБКА'}")
    
    if is_valid:
        print("Теперь вы можете:")
        print("• Распространять подписанное видео")
        print("• Проверять его подлинность без оригинала")
        print("• Гарантировать, что видео не изменено")

if __name__ == "__main__":
    try:
        import gostcrypto
        print("Библиотека gostcrypto успешно импортирована")
        print()
        
        # Простая демонстрация
        simple_demo()
        
    except ImportError:
        print("Ошибка: Библиотека gostcrypto не установлена!")
        print("Установите её командой: pip install gostcrypto")
    except Exception as e:
        print(f"Произошла ошибка: {e}")
        import traceback
        traceback.print_exc()
