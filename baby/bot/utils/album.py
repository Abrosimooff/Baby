
class AlbumPager(object):
    object_list = []  # Все элементы альбома по очереди (т.е элементы одного месяца)
    css_classes = ['pos-left-top', 'pos-right-top', 'pos-left-bottom', 'pos-right-bottom', ]
    CHUNK_TEXT_CHARS = 250
    MAX_TITLE_CHARS = 50

    def __init__(self) -> None:
        super().__init__()
        self.object_list = []

    def add(self, history, photo_list):
        if history.text and len(history.text) > self.MAX_TITLE_CHARS:
            if len(history.text) <= self.CHUNK_TEXT_CHARS:
                history.is_text = True
                self.object_list.append(history)
            else:
                text_parts = self.chunks_text(history.text)
                for num, text in enumerate(text_parts, 1):
                    class PartHistory:
                        def __init__(self, text, date_vk):
                            self.text = text
                            self.date_vk = date_vk
                            self.month = None
                            self.is_text = True
                            if num < len(text_parts):
                                self.text += ' ...'

                    self.object_list.append(PartHistory(text, history.date_vk))

        else:
            if not photo_list:  # Если текст маленький, как подпись к фото, но фотографий нет, то считаем этот текстом
                history.is_text = True
                self.object_list.append(history)

        for index, photo in enumerate(photo_list):
            history_text = not index and history.text and len(
                history.text) <= self.MAX_TITLE_CHARS and history.text or ''
            self.object_list.append(Photo(photo, history.date_vk if history.month is None else None, history_text))

    def add_measure(self, measure_list):
        """Добавить измерения Рост/Вес"""
        self.object_list.extend(measure_list)


    def chunks_text(self, text):
        result = []
        count = self.CHUNK_TEXT_CHARS
        pos_space = 0  # Позиция первого пробела после конца делимой строки (делим на моменте пробела)
        for i in range(0, len(text), count):
            start = i + pos_space
            pos_space = text[start + count:].find(' ')
            if pos_space == -1:
                pos_space = len(text)
                result.append(text[start:pos_space])
                break
            result.append(text[start:i+count+pos_space])

        return result

    def chunks_pages(self, object_list, count):
        result = []
        for i in range(0, len(object_list), count):
            page_items = []
            for element_index, item in enumerate(object_list[i:i + count]):
                page_items.append(dict(
                    object=item,
                    css_class_pos=self.css_classes[element_index]
                ))
            result.append(page_items)
        return result

    @property
    def page_list(self):
        return self.chunks_pages(self.object_list, 4)


class Photo(object):
    id = None
    url = None
    date = None
    title = None
    is_photo = True
    background_position = None

    def __init__(self, obj, date, title):
        self.id = obj.id
        self.url = obj.url
        self.date = date
        self.title = title
        self.background_position = obj.background_position or 'center center'

class Album(object):

    def __init__(self, baby_id):
        pass