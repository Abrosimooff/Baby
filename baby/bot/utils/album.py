
class AlbumPager(object):
    object_list = []  # Все элементы альбома по очереди (т.е элементы одного месяца)
    css_classes = ['pos-left-top', 'pos-right-top', 'pos-left-bottom', 'pos-right-bottom', ]
    CHUNK_TEXT_CHARS = 200
    MAX_TITLE_CHARS = 50

    def __init__(self) -> None:
        super().__init__()
        self.object_list = []

    def add(self, history, photo_list):

        if history.text and len(history.text) > self.MAX_TITLE_CHARS:
            if len(history.text) <= self.CHUNK_TEXT_CHARS:
                self.object_list.append(history)
            else:
                text_parts = self.chunks_text(history.text)
                for num, text in enumerate(text_parts, 1):
                    class PartHistory:
                        def __init__(self, text, date_vk):
                            self.text = text
                            self.date_vk = date_vk
                            self.month = None
                            if num < len(text_parts):
                                self.text += ' ...'

                    self.object_list.append(PartHistory(text, history.date_vk))

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
        for i in range(0, len(text), count):
            result.append(text[i:i + count])
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
    url = None
    date = None
    title = None
    is_photo = True

    def __init__(self, url, date, title):
        self.url = url
        self.date = date
        self.title = title

class Album(object):

    def __init__(self, baby_id):
        pass