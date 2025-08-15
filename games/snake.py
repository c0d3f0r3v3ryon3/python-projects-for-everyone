# snake.py - Змейка в терминале (без ошибок)
import curses
import random
import time

def main(stdscr):
    curses.curs_set(0)  # Скрыть курсор
    stdscr.timeout(100)  # Скорость
    sh, sw = stdscr.getmaxyx()
    max_y = sh - 2
    max_x = sw - 2
    snake = [(max_y // 2, max_x // 2)]
    food = (random.randint(1, max_y), random.randint(1, max_x))
    direction = curses.KEY_RIGHT
    try:
        stdscr.addch(food[0], food[1], ord('@'))
    except curses.error:
        pass  # если не получилось — не страшно
    while True:
        stdscr.clear()
        for y in range(1, max_y + 1):
            try:
                stdscr.addch(y, 1, ord('|'))        # лево
                stdscr.addch(y, max_x, ord('|'))     # право
            except:
                pass
        for x in range(1, max_x + 1):
            try:
                stdscr.addch(1, x, ord('-'))         # верх
                stdscr.addch(max_y, x, ord('-'))     # низ
            except:
                pass
        try:
            stdscr.addch(1, 1, ord('+'))             # верх-лево
            stdscr.addch(1, max_x, ord('+'))         # верх-право
            stdscr.addch(max_y, 1, ord('+'))         # низ-лево
            stdscr.addch(max_y, max_x, ord('+'))     # низ-право
        except:
            pass
        for y, x in snake:
            if 1 <= y <= max_y and 1 <= x <= max_x:
                try:
                    stdscr.addch(y, x, ord('O'))
                except:
                    pass
        try:
            stdscr.addch(food[0], food[1], ord('@'))
        except:
            pass
        key = stdscr.getch()
        if key in [curses.KEY_UP, curses.KEY_DOWN, curses.KEY_LEFT, curses.KEY_RIGHT]:
            direction = key
        head = snake[0]
        if direction == curses.KEY_RIGHT:
            new_head = (head[0], head[1] + 1)
        elif direction == curses.KEY_LEFT:
            new_head = (head[0], head[1] - 1)
        elif direction == curses.KEY_UP:
            new_head = (head[0] - 1, head[1])
        elif direction == curses.KEY_DOWN:
            new_head = (head[0] + 1, head[1])
        else:
            new_head = head
        snake.insert(0, new_head)
        if new_head == food:
            food = (random.randint(1, max_y), random.randint(1, max_x))
            try:
                stdscr.addch(food[0], food[1], ord('@'))
            except:
                pass
        else:
            tail = snake.pop()
            try:
                if 1 <= tail[0] <= max_y and 1 <= tail[1] <= max_x:
                    stdscr.addch(tail[0], tail[1], ' ')
            except:
                pass
        if (new_head[0] < 1 or new_head[0] > max_y or
            new_head[1] < 1 or new_head[1] > max_x or
            new_head in snake[1:]):
            try:
                stdscr.addstr(max_y // 2, max_x // 2 - 5, "GAME OVER")
                stdscr.refresh()
            except:
                pass
            time.sleep(2)
            break
if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except Exception as e:
        print(f"Ошибка: {e}")
        input("Нажми Enter, чтобы выйти...")
