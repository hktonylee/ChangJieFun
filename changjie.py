#!/bin/env python
# -*- encoding: utf-8

import codecs
import sys, tty, termios


class InputMethod:
    def __init__(self):
        self._wordMap = {}

    def add(self, stroke, character):
        lst = self._wordMap.setdefault(stroke, [])
        lst.append(character)

    def get(self, stroke):
        return self._wordMap[stroke]


WORDS = '!'

class InputMethod2:
    def __init__(self):
        self._wordMap = {}

    def add(self, stroke, character):
        d = self._wordMap
        n = len(stroke)
        for i in range(n):
            d = d.setdefault(stroke[i], {})
        d.setdefault(WORDS, []).append(character)

    def get(self, stroke):
        try:
            d = self._wordMap
            for ch in stroke:
                d = d[ch]
            return d[WORDS]
        except KeyError:
            return []

    def get_generator(self, stroke):
        d = self._wordMap
        for ch in stroke:
            d = d[ch]
        for item in d[WORDS]:
            yield item
        for ch in d:
            if ch != WORDS:
                words = d[ch].get(WORDS, None)
                if words is not None:
                    for item in words:
                        yield item




KEY_CTRL_C = '\x03'
KEY_DELETE = ['\x10', '\x7F']
KEY_ENTER = '\x0D'
KEY_BACKSPACE = '\x08'
KEY_ESCAPE = '\x1B'

class InteractivePrompt(object):
    def __init__(self):
        pass

    def read_ch(self):
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch

    def run(self):
        while True:
            ch = self.read_ch()
            if ch == KEY_CTRL_C and self.on_ctrl_c():
                return
            elif ch in KEY_DELETE:
                self.on_delete()
            elif ch == KEY_ENTER:
                self.on_enter()
            elif ch == KEY_ESCAPE:
                self.on_escape()
            else:

                self.on_input(ch)

    def on_ctrl_c(self):
        sys.stdout.write('\n')
        return True

    def on_input(self, ch):
        pass

    def on_enter(self):
        pass

    def on_delete(self):
        pass

    def on_escape(self):
        pass


class BasicInteractivePrompt(InteractivePrompt):
    def on_input(self, ch):
        sys.stdout.write(ch)
        sys.stdout.write(' ')
        sys.stdout.write(hex(ord(ch)))
        sys.stdout.write(' ')

    def on_enter(self):
        sys.stdout.write('ENTER ')

    def on_delete(self):
        sys.stdout.write(KEY_BACKSPACE)

STATE_INPUT_STROKE = 1
STATE_SELECT_CHARACTER = 2

class ChangJieInteractivePrompt(InteractivePrompt):
    def __init__(self):
        super(ChangJieInteractivePrompt, self).__init__()
        self._strokes = ""
        self._state = STATE_INPUT_STROKE
        self._selecting_characters = []
        self._selecting_characters_length = 0

    def on_ctrl_c(self):
        sys.stdout.write('\n')
        return True

    def on_input(self, ch):
        if self._state == STATE_INPUT_STROKE:
            if ch == ' ':
                self._input_stroke()
            elif ch.isalpha():
                self._strokes += ch.lower();
                sys.stdout.write(ch)
        elif self._state == STATE_SELECT_CHARACTER:
            if ch.isdigit():
                n = (int(ch) - 1) % 10
                if n < len(self._selecting_characters):
                    self._select_character(n)
            elif ch == ' ':
                self._select_character(0)
            elif ch.isalpha():
                self._select_character(0)
                self._strokes += ch.lower();
                sys.stdout.write(ch)

    def on_enter(self):
        if self._state == STATE_INPUT_STROKE:
            self._input_stroke()
        elif self._state == STATE_SELECT_CHARACTER:
            self._select_character(0)

    def on_delete(self):
        if self._state == STATE_INPUT_STROKE:
            if len(self._strokes) > 0:
                sys.stdout.write(KEY_BACKSPACE + ' ' + KEY_BACKSPACE)
                self._strokes = self._strokes[:-1]
            else:
                self._clear_buffer(2)
        elif self._state == STATE_SELECT_CHARACTER:
            self._clear_select_characters()
            self._state = STATE_INPUT_STROKE

    def _select_character(self, n):
        ch = self._selecting_characters[n]
        self._clear_select_characters()
        sys.stdout.write(ch)
        self._state = STATE_INPUT_STROKE

    def _clear_buffer(self, n, clear_before=True, clear_after=True):
        if clear_before:
            sys.stdout.write(KEY_BACKSPACE * n)
        sys.stdout.write(' ' * n)
        if clear_after:
            sys.stdout.write(KEY_BACKSPACE * n)

    def _clear_stroke(self):
        if len(self._strokes) > 0:
            self._clear_buffer(len(self._strokes))
            self._strokes = ""

    def _clear_select_characters(self):
        self._clear_buffer(self._selecting_characters_length, clear_before=False)
        self._selecting_characters_length = 0
        self._selecting_characters = []

    def _input_stroke(self):
        if self._state == STATE_INPUT_STROKE:
            characters = chang_jie.get(self._strokes)[:10]
            if len(characters) >= 2:
                self._clear_stroke()
                sys.stdout.write(' ')
                out = ""
                for i, ch in enumerate(characters):
                    out += str((i + 1) % 10) + ' ' + ch + ' '
                sys.stdout.write(out)
                self._selecting_characters_length = len(out) + len(characters) + 1
                sys.stdout.write(KEY_BACKSPACE * self._selecting_characters_length)
                self._state = STATE_SELECT_CHARACTER
                self._selecting_characters = characters
            elif len(characters) == 1:
                self._clear_stroke()
                sys.stdout.write(characters[0])

    def on_escape(self):
        if self._state == STATE_INPUT_STROKE:
            self._clear_stroke()
        elif self._state == STATE_SELECT_CHARACTER:
            self._clear_select_characters()
            self._state = STATE_INPUT_STROKE

def load_chang_jie():
    with open('cj5-21000', 'rb') as f:
        content = f.read()
        bom = codecs.BOM_UTF16_LE
        assert content.startswith(bom)
        content = content[len(bom):].decode('utf-16le')
        content_started = False
        for line in content.splitlines():
            if line == '[Text]':
                content_started = True
            elif content_started:
                stroke = line[1:]
                character = line[0]
                if len(character.encode('utf-8')) > 0:
                    chang_jie.add(stroke, character)

def print_stroke(stroke):
    print stroke, ':\t',
    lst = chang_jie.get(stroke)
    for ch in lst:
        print ch,
    print

def print_list(lst):
    for ch in lst:
        print ch,
    print


# chang_jie = InputMethod()
chang_jie = InputMethod2()
load_chang_jie()

prompt = ChangJieInteractivePrompt()

prompt.run()

# print_stroke('hqi')
# print_stroke('oan')
# print_stroke('janl')
# print_stroke('amyo')
# print_stroke('jd')
# print_stroke('doo')
# print_stroke('hapi')
# print_stroke('yg')
# print_stroke('o')
# print_stroke('cism')

# print_stroke('vfog')
# print_stroke('opd')
# print_stroke('djpn')
# print_stroke('dtbo')
# print_stroke('tod')
# print_stroke('vnd')
# print_stroke('oino')


# print list(chang_jie.get_generator('hq'))
# print 'hq :\t',
# print print_list(list(chang_jie.get_generator('hq')))


