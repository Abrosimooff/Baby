START_LINE = [
    dict(
        name='start1',
        text='Привет. Для начала расскажи кто у тебя! Мальчик? Девочка?',
        variants=[dict(
            text='Мальчик', next='')],
        next=dict(
            name='start2',
            text='Отлично. расскажи как зовут твоего ребёнка',
        )
    )
]