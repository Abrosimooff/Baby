DEFAULT_KEYBOARD = dict(
    one_time=True,
    buttons=[
        [
        dict(
            action=dict(
                type="text",
                label=u'Ввести рост',
                payload=dict(action='/height/0/')
            ),
            color="secondary"
        ),
        dict(
            action=dict(
                type="text",
                label=u'Ввести вес',
                payload=dict(action='/weight/0/')
            ),
            color="secondary"
        ),
    ],
    [
        dict(
            action=dict(
                type="text",
                label=u'Настройки',
                payload=dict(action='/settings/-1/')
            ),
            color="secondary"
        ),
        dict(
            action=dict(
                type="text",
                label=u'Получить альбом',
                payload=dict(action='/album')
            ),
            color="secondary"
        )
     ],
    [
        dict(
            action=dict(
                type="text",
                label=u'Поделиться',
                payload=dict(action='/sharing/')
            ),
            color="secondary"
        ),
        dict(
            action=dict(
                type="text",
                label=u'Помощь',
                payload=dict(action='/help/')
            ),
            color="secondary"
        ),
    ],
    [
        dict(
            action=dict(
                type="text",
                label=u'Добавить в прошлое',
                payload=dict(action='past/months/0/')
            ),
            color="secondary"
        )
    ]
    ]
 )
