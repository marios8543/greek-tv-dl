class BaseShow:
    title = ""
    link = ""

    def to_dict(self):
        return {
            "title": self.title,
            "link": self.link,
            "id": self.id
        }

    def __str__(self):
        return self.title

    @property
    def id(self):
        return str(abs(hash(self.title)))

class BaseEpisode:
    title = ""
    downloading = False

    def to_dict(self):
        return {
            "title": self.title,
            "id": self.id
        }

    def __str__(self):
        return self.title

    @property
    def id(self):
        return str(abs(hash(self.title)))