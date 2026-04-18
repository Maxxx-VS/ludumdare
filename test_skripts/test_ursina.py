from ursina import *

app = Ursina()

# Создаем вращающийся куб
cube = Entity(model='cube', color=color.orange, scale=(2,2,2), texture='white_cube')

def update():
    cube.rotation_y += time.dt * 100
    cube.rotation_x += time.dt * 50

app.run()
