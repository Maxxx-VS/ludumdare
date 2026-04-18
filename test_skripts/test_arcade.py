import arcade

arcade.open_window(800, 600, "Jetson Arcade Test")
arcade.set_background_color(arcade.color.AMAZON)

arcade.start_render()
# Рисуем круг в центре
arcade.draw_circle_filled(400, 300, 50, arcade.color.YELLOW)
arcade.finish_render()

arcade.run()

