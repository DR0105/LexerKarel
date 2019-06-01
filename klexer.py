# -*- coding: utf-8 -*-

import sys
from kutil import KarelException, ktoken


class klexer(object):
    """analizador léxico de karel"""
    ESTADO_ESPACIO = ' '
    ESTADO_PALABRA = 'a'
    ESTADO_COMENTARIO = '#'
    ESTADO_NUMERO = '0'
    ESTADO_SIMBOLO = '+'
    def __init__(self, archivo=sys.stdin, nombre_archivo='codigo.txt', debug=False):
        self.archivo = archivo
        self.nombre_archivo = nombre_archivo

        self.numeros = "0123456789"
        self.palabras = "abcdfeghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_-"
        self.simbolos = "(){}*/;,|&!#" 
        self.espacios = " \n\r\t"

        self.caracteres = self.numeros+self.palabras+self.simbolos+self.espacios

        self.ultimo_caracter = ''
        self.caracter_actual = ''
        self.abrir_comentario = '' 

        self.pila_tokens = [] 

        self.linea = 1 
        self.columna = 0
        self.es_primer_token = True
        self.token = ''
        self.estado = self.ESTADO_ESPACIO

        self.sintaxis = 'pascal' 
        self.lonely_chars = [';', '{', '}', '!', ')', '#']

        self.debug = debug
        self.caracter_actual = self.lee_caracter()
        if self.debug:
            print "leyendo archivo '%s'"%self.nombre_archivo

    def lee_caracter(self):
        self.ultimo_caracter = self.caracter_actual
        return self.archivo.read(1)

    def get_token(self):
        
        if len(self.pila_tokens)>0:
            return self.pila_tokens.pop()
        else:
            return self.lee_token()

    def push_token(self, token):
        self.pila_tokens.append(token)

    def cambio_de_linea(self):
        self.linea += 1
        self.columna = 0
        self.es_primer_token = True

    def lee_token(self):
        while True:
            self.columna += 1
            if not self.caracter_actual:
                break
            if self.estado == self.ESTADO_COMENTARIO:
                if self.debug:
                    print "Encontré", repr(self.caracter_actual), 
                if self.caracter_actual in self.simbolos: 
                    if self.caracter_actual == ')' and self.abrir_comentario == '(*' and self.ultimo_caracter == '*':
                        self.estado = self.ESTADO_ESPACIO
                    if self.caracter_actual == '}' and self.abrir_comentario == '{':
                        self.estado = self.ESTADO_ESPACIO
                    if self.caracter_actual == '/' and self.abrir_comentario == '/*' and self.ultimo_caracter == '*':
                        self.estado = self.ESTADO_ESPACIO
                if self.caracter_actual == '\n': 
                    self.cambio_de_linea()
            elif self.estado == self.ESTADO_ESPACIO:
                if self.debug:
                    print "Encontré", repr(self.caracter_actual), 
                if self.caracter_actual not in self.caracteres:
                    raise KarelException("Caracter desconocido en la linea %d columna %d"%(self.linea, self.columna))
                if self.caracter_actual in self.numeros:
                    self.token += self.caracter_actual
                    self.estado = self.ESTADO_NUMERO
                elif self.caracter_actual in self.palabras:
                    self.token += self.caracter_actual
                    self.estado = self.ESTADO_PALABRA
                elif self.caracter_actual in self.simbolos:
                    self.estado = self.ESTADO_SIMBOLO
                    continue
                elif self.caracter_actual == '\n': #LINEA
                    self.cambio_de_linea()
            elif self.estado == self.ESTADO_NUMERO:
                if self.debug:
                    print "Encontré", repr(self.caracter_actual), "en estado número"
                if self.caracter_actual not in self.caracteres:
                    raise KarelException("Caracter desconocido en la linea %d columna %d"%(self.linea, self.columna))
                if self.caracter_actual in self.numeros:
                    self.token += self.caracter_actual
                elif self.caracter_actual in self.palabras: #Encontramos una letra en el estado numero, incorrecto
                    raise KarelException("Este token no parece valido, linea %d columna %d"%(self.linea, self.columna))
                elif self.caracter_actual in self.simbolos:
                    self.estado = self.ESTADO_SIMBOLO
                    break
                elif self.caracter_actual in self.espacios:
                    self.estado = self.ESTADO_ESPACIO
                    break #Terminamos este token
            elif self.estado == self.ESTADO_PALABRA:
                if self.debug:
                    print "Encontré", repr(self.caracter_actual), 
                if self.caracter_actual not in self.caracteres:
                    raise KarelException("Caracter desconocido en la linea %d columna %d"%(self.linea, self.columna))
                if self.caracter_actual in self.palabras+self.numeros:
                    self.token += self.caracter_actual
                elif self.caracter_actual in self.simbolos:
                    self.estado = self.ESTADO_SIMBOLO
                    break
                elif self.caracter_actual in self.espacios:
                    self.estado = self.ESTADO_ESPACIO
                    break #Terminamos este token
            elif self.estado == self.ESTADO_SIMBOLO:
                if self.debug:
                    print "Encontré", repr(self.caracter_actual), 
                if self.caracter_actual not in self.caracteres:
                    raise KarelException("Caracter desconocido en la linea %d columna %d"%(self.linea, self.columna))
                if self.caracter_actual == '{' and self.sintaxis=='pascal':
                    self.abrir_comentario = '{'
                    self.estado = self.ESTADO_COMENTARIO
                    if self.token:
                        break
                elif self.caracter_actual == '#':
                    self.estado = self.ESTADO_ESPACIO
                    self.archivo.readline() 
                    self.cambio_de_linea()
                    if self.token:
                        break
                elif self.caracter_actual in self.numeros:
                    self.estado = self.ESTADO_NUMERO
                    if self.token:
                        break
                elif self.caracter_actual in self.palabras:
                    self.estado = self.ESTADO_PALABRA
                    if self.token:
                        break
                elif self.caracter_actual in self.simbolos: 
                    if self.caracter_actual == '/' and self.ultimo_caracter == '/':
                        self.archivo.readline() 
                        self.cambio_de_linea()
                        self.estado = self.ESTADO_ESPACIO
                        if self.token.endswith('/'):
                            self.token = self.token[:-1]
                        if self.token:
                            self.caracter_actual = self.lee_caracter()
                            break
    
                    elif self.caracter_actual == '*' and self.ultimo_caracter == '(' and self.sintaxis == 'pascal':
                        self.estado = self.ESTADO_COMENTARIO
                        self.abrir_comentario = '(*'
                        if self.token.endswith('('):
                            self.token = self.token[:-1]
                        if self.token:
                            self.caracter_actual = self.lee_caracter()
                            break
                    elif self.caracter_actual in self.lonely_chars: 
                        self.estado = self.ESTADO_ESPACIO
                        if self.token:
                            break
                        self.token += self.caracter_actual
                        self.caracter_actual = self.lee_caracter()
                        break
                    else:
                        self.token += self.caracter_actual
                elif self.caracter_actual in self.espacios:
                    self.estado = self.ESTADO_ESPACIO
                    if self.token:
                        break
                else:
                    raise KarelException("Caracter desconocido en la linea %d columna %d"%(self.linea, self.columna))
            self.caracter_actual = self.lee_caracter()
        token = self.token
        self.token = ''
        obj_token = ktoken(token, self.es_primer_token)
        self.es_primer_token = False
        return obj_token

    def __iter__(self):
        return self

    def next(self):
        token = self.get_token()
        if token == '':
            raise StopIteration
        return token


if __name__ == '__main__':
    lexer = klexer(open(sys.argv[0]), sys.argv[0], debug=debug)
    debug=0
    if '-d' in sys.argv:
        debug=1
    i=0
    for token in lexer:
        print "Token:", repr(token), "\t\tLine:", lexer.linea, "\t\tCol:", lexer.columna, "\t\tPrimer:", token.es_primer_token
        i += 1
    print lexer.sintaxis
    print "Hubo", i, "tokens"
