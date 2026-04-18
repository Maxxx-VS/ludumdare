from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController

app = Ursina()

# Окружение
ground = Entity(model='plane', collider='box', scale=64, texture='white_cube', texture_scale=(64,64))
wall = Entity(model='cube', collider='box', position=(0,1,5), scale=(3,2,1), color=color.azure)

# Игрок
player = FirstPersonController()
player.cursor.visible = True # Чтобы видеть прицел

def input(key):
    # Быстрый выход на ESC
    if key == 'escape':
        quit()
    
    # Пример взаимодействия
    if key == 'left mouse down':
        if mouse.hovered_entity:
            destroy(mouse.hovered_entity)

def update():
    # Простая логика: если игрок упал под текстуры
    if player.y < -10:
        player.position = (0, 5, 0)

# Небо и свет
Sky()
DirectionalLight(y=2, z=3, shadows=True)

app.run()
