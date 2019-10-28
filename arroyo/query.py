from arroyo import normalize


class Query(dict):
    def __init__(self, type, **kwargs):
        if type not in normalize.ENTITIES_DEFS:
            raise TypeError(type)

        kwargs['type'] = type
        super().__init__(**kwargs)

    @classmethod
    def fromstring(cls, s):
        entity, _, _ = normalize.parse(s)
        return cls(**entity)
