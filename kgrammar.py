#!/usr/bin/env python
# -*- coding: utf-8 -*-
__all__ = ['kgrammar']

from klexer import klexer
from string import ascii_letters
from collections import deque
from pprint import pprint
import json
import sys

class KarelException(Exception):
    pass

class kgrammar:
    def __init__(self, flujo=sys.stdin, archivo='codigo.txt', strict=True, strong_logic=False):
        self.strict = strict
        self.tiene_apagate = False
        self.instrucciones = ['avanza', 'gira-izquierda', 'coge-zumbador', 'deja-zumbador', 'apagate', 'sal-de-instruccion', 'sal-de-bucle', 'continua-bucle']
    
        self.condiciones = [
            'frente-libre',
            'derecha-libre',
            'izquierda-libre',
            'junto-a-zumbador',
            'algun-zumbador-en-la-mochila',
            "orientado-al-norte",
            "orientado-al-este",
            "orientado-al-sur",
            "orientado-al-oeste",
            "no-orientado-al-oeste",
            "no-orientado-al-norte",
            "no-orientado-al-sur",
            "no-orientado-al-este",
            'no-junto-a-zumbador',
            'derecha-bloqueada',
            'frente-bloqueado',
            'izquierda-bloqueada',
            'ningun-zumbador-en-la-mochila',
            "si-es-cero",
            "verdadero", 
            "falso" 
        ]
        if strong_logic: 
            self.condiciones = self.condiciones[:9] + self.condiciones[18:]
        self.expresiones_enteras = ['sucede', 'precede']

        self.estructuras = ['si', 'mientras', 'repite', 'repetir']

        self.palabras_reservadas = [
            "iniciar-programa",
            "inicia-ejecucion",
            "termina-ejecucion",
            "finalizar-programa",
            "no",
            "y",
            "o",
            "u",
            "define-nueva-instruccion",
            "define-prototipo-instruccion",
            "inicio",
            "fin",
            "hacer",
            "veces",
            "entonces",
            "sino"
        ] + self.instrucciones + self.condiciones + self.expresiones_enteras + self.estructuras

        self.lexer = klexer(flujo, archivo)
        self.token_actual = self.lexer.get_token()
        self.funciones = dict()
        self.llamadas_funciones = dict()
        self.arbol = {
            "main": [], 
            "funciones": dict() 
        }
        
        self.lista_programa = deque()
        self.ejecutable = {
            'lista': deque(),
            'indice_funciones': dict(),
            'main': 0
        }
        
        self.sintaxis = 'pascal' 
    def obtener_linea_error(self):
        if self.token_actual.es_primer_token:
            return self.lexer.linea - 1
        else:
            return self.lexer.linea

    def avanza_token (self):
       
        siguiente_token = self.lexer.get_token()

        if siguiente_token:
            if self.sintaxis == 'pascal':
                siguiente_token.lower()
            self.token_actual = siguiente_token
            return True
        else:
            return False

    def bloque(self):

        while self.token_actual == 'define-nueva-instruccion' or self.token_actual == 'define-prototipo-instruccion' or self.token_actual == 'externo':
            if self.token_actual == 'define-nueva-instruccion':
                self.declaracion_de_procedimiento()
        if self.token_actual == 'inicia-ejecucion':
            self.avanza_token()
            self.arbol['main'] = self.expresion_general([], False, False)
            if self.token_actual != 'termina-ejecucion':
                raise KarelException("Se esperaba 'termina-ejecucion' al final del bloque lógico del programa, encontré '%s'"%self.token_actual)
            else:
                self.avanza_token()

    def clausula_atomica(self, lista_variables):
        retornar_valor = None

        if self.token_actual == 'si-es-cero':
            self.avanza_token()
            if self.token_actual == '(':
                self.avanza_token()
                retornar_valor = {'si-es-cero': self.expresion_entera(lista_variables)}
                if self.token_actual == ')':
                    self.avanza_token()
                else:
                    raise KarelException("Se esperaba ')'")
            else:
                raise KarelException("Se esperaba '(' para indicar argumento de 'si-es-cero'")
        elif self.token_actual == '(':
            self.avanza_token()
            retornar_valor = self.termino(lista_variables)
            if self.token_actual == ')':
                self.avanza_token()
            else:
                raise KarelException("Se esperaba ')'")
        else:
            retornar_valor = self.funcion_booleana()

        return retornar_valor

    def clausula_no(self, lista_variables):
        retornar_valor = None

        if self.token_actual == 'no':
            self.avanza_token()
            retornar_valor = {'no': self.clausula_atomica(lista_variables)}
        else:
            retornar_valor = self.clausula_atomica(lista_variables)

        return retornar_valor

    def clausula_y(self, lista_variables):
        retornar_valor = {'y': [self.clausula_no(lista_variables)]}

        while self.token_actual == 'y':
            self.avanza_token()
            retornar_valor['y'].append(self.clausula_no(lista_variables))

        return retornar_valor

    def declaracion_de_procedimiento(self):

        self.avanza_token()

        requiere_parametros = False 
        nombre_funcion = ''

        if self.token_actual in self.palabras_reservadas or not self.es_identificador_valido(self.token_actual):
            raise KarelException("Se esperaba un nombre de procedimiento vÃ¡lido, '%s' no lo es"%self.token_actual)

        if self.funciones.has_key(self.token_actual):
            raise KarelException("Ya se ha definido una funcion con el nombre '%s'"%self.token_actual)
        else:
            self.funciones.update({self.token_actual: []})
            nombre_funcion = self.token_actual

        self.arbol['funciones'].update({
            nombre_funcion : {
                'params': [],
                'cola': []
            }
        })

        self.avanza_token()

        if self.token_actual == 'como':
            self.avanza_token()
        elif self.token_actual == '(':
            self.avanza_token()
            requiere_parametros = True
            while True:
                if self.token_actual in self.palabras_reservadas or not self.es_identificador_valido(self.token_actual):
                    raise KarelException("Se esperaba un nombre de variable, '%s' no es válido"%self.token_actual)
                else:
                    if self.token_actual in self.funciones[nombre_funcion]:
                        raise KarelException("La funcion '%s' ya tiene un parámetro con el nombre '%s'"%(nombre_funcion, self.token_actual))
                    else:
                        self.funciones[nombre_funcion].append(self.token_actual)
                        self.avanza_token()

                    if self.token_actual == ')':
                        self.lexer.push_token(')') 
                        break
                    elif self.token_actual == ',':
                        self.avanza_token()
                    else:
                        raise KarelException("Se esperaba ',', encontré '%s'"%self.token_actual)
            self.arbol['funciones'][nombre_funcion]['params'] = self.funciones[nombre_funcion]
        else:
            raise KarelException("Se esperaba la palabra clave 'como' o un parametro")

        if requiere_parametros:
            self.avanza_token()
            if self.token_actual != ')':
                raise KarelException("Se esperaba ')'")
            self.avanza_token()
            if self.token_actual != 'como':
                raise KarelException("se esperaba la palabra clave 'como'")
            self.avanza_token()

        if self.prototipo_funciones.has_key(nombre_funcion):
            if len(self.prototipo_funciones[nombre_funcion]) != len(self.funciones[nombre_funcion]):
                raise KarelException("La función '%s' no está definida como se planeó en el prototipo, verifica el número de variables"%nombre_funcion)

        self.arbol['funciones'][nombre_funcion]['cola'] = self.expresion(self.funciones[nombre_funcion], True, False)

        if self.token_actual != ';':
            raise KarelException("Se esperaba ';'")
        else:
            self.avanza_token()



    def expresion(self, lista_variables, c_funcion, c_bucle):
        
        retornar_valor = []

        if self.token_actual in self.instrucciones:
            if self.token_actual == 'sal-de-instruccion':
                if c_funcion:
                    retornar_valor = [self.token_actual]
                    self.avanza_token()
                else:
                    raise KarelException("No es posible usar 'sal-de-instruccion' fuera de una instruccion :)")
            elif self.token_actual == 'sal-de-bucle' or self.token_actual == 'continua-bucle':
                if c_bucle:
                    retornar_valor = [self.token_actual]
                    self.avanza_token()
                else:
                    raise KarelException("No es posible usar '"+self.token_actual.token+"' fuera de un bucle :)")
            else:
                if self.token_actual == 'apagate':
                    self.tiene_apagate = True
                retornar_valor = [self.token_actual]
                self.avanza_token()
        elif self.token_actual == 'si':
            retornar_valor = [self.expresion_si(lista_variables, c_funcion, c_bucle)]
        elif self.token_actual == 'mientras':
            retornar_valor = [self.expresion_mientras(lista_variables, c_funcion)]
        elif self.token_actual == 'repite' or self.token_actual == 'repetir':
            retornar_valor = [self.expresion_repite(lista_variables, c_funcion)]
        elif self.token_actual == 'inicio':
            self.avanza_token()
            retornar_valor = self.expresion_general(lista_variables, c_funcion, c_bucle)
            if self.token_actual == 'fin':
                self.avanza_token()
            else:
                raise KarelException("Se esperaba 'fin' para concluir el bloque, encontré '%s'"%self.token_actual)
        elif self.token_actual not in self.palabras_reservadas and self.es_identificador_valido(self.token_actual):
            
            if self.prototipo_funciones.has_key(self.token_actual) or self.funciones.has_key(self.token_actual):
                nombre_funcion = self.token_actual
                retornar_valor = [{
                    'estructura': 'instruccion',
                    'nombre': nombre_funcion,
                    'argumento': []
                }]
                self.avanza_token()
                requiere_parametros = True
                num_parametros = 0
                if self.token_actual == '(':
                    self.avanza_token()
                    while True:
                        retornar_valor[0]['argumento'].append(self.expresion_entera(lista_variables))
                        num_parametros += 1
                        if self.token_actual == ')':
                            self.lexer.push_token(')')
                            break
                        elif self.token_actual == ',':
                            self.avanza_token()
                        else:
                            raise KarelException("Se esperaba ',', encontré '%s'"%self.token_actual)
                    if not self.futuro and num_parametros>1:
                        raise KarelException("No están habilitadas las funciones con varios parámetros")
                    self.avanza_token()
                if self.prototipo_funciones.has_key(nombre_funcion):
                    if num_parametros != len(self.prototipo_funciones[nombre_funcion]):
                        raise KarelException("Estas intentando llamar la funcion '%s' con %d parámetros, pero así no fue definida"%(nombre_funcion, num_parametros))
                else:
                    if num_parametros != len(self.funciones[nombre_funcion]):
                        raise KarelException("Estas intentando llamar la funcion '%s' con %d parámetros, pero así no fue definida"%(nombre_funcion, num_parametros))
            else:
                raise KarelException("La instrucción '%s' no ha sido previamente definida, pero es utilizada"%self.token_actual)
        else:
            raise KarelException("Se esperaba un procedimiento, '%s' no es válido"%self.token_actual)

        return retornar_valor

    def expresion_entera(self, lista_variables):
        
        retornar_valor = None
        
        es_numero = False
        if self.es_numero(self.token_actual):
            
            retornar_valor = int(self.token_actual)
            es_numero = True
        else:
           
            if self.token_actual in self.expresiones_enteras:
                retornar_valor = {
                    self.token_actual: None
                }
                self.avanza_token()
                if self.token_actual == '(':
                    self.avanza_token()
                    retornar_valor[retornar_valor.keys()[0]] = self.expresion_entera(lista_variables)
                    if self.token_actual == ')':
                        self.avanza_token()
                    else:
                        raise KarelException("Se esperaba ')'")
                else:
                    raise KarelException("Se esperaba '(' para indicar argumento de precede o sucede")
            elif self.token_actual not in self.palabras_reservadas and self.es_identificador_valido(self.token_actual):
                
                if self.token_actual not in lista_variables:
                    raise KarelException("La variable '%s' no está definida en este contexto"%self.token_actual)
                retornar_valor = self.token_actual
                self.avanza_token()
            else:
                raise KarelException("Se esperaba un entero, variable, sucede o predece, '%s' no es válido"%self.token_actual)
        if es_numero:
            self.avanza_token()

        return retornar_valor

    def expresion_general(self, lista_variables, c_funcion, c_bucle):
        retornar_valor = [] 
        while self.token_actual != 'fin' and self.token_actual != 'termina-ejecucion':
            retornar_valor += self.expresion(lista_variables, c_funcion, c_bucle)
            if self.token_actual != ';' and self.token_actual != 'fin' and self.token_actual != 'termina-ejecucion':
                raise KarelException("Se esperaba ';'")
            elif self.token_actual == ';':
                self.avanza_token()
            elif self.token_actual == 'fin':
                raise KarelException("Se esperaba ';'")
            elif self.token_actual == 'termina-ejecucion':
                raise KarelException("Se esperaba ';'")

        return retornar_valor

    def expresion_mientras(self, lista_variables, c_funcion):
        retornar_valor = {
            'estructura': 'mientras',
            'argumento': None,
            'cola': []
        }
        self.avanza_token()

        retornar_valor['argumento'] = self.termino(lista_variables)

        if self.token_actual != 'hacer':
            raise KarelException("Se esperaba 'hacer'")
        self.avanza_token()
        retornar_valor['cola'] = self.expresion(lista_variables, c_funcion, True)

        return retornar_valor

    def expresion_repite(self, lista_variables, c_funcion):
        
        retornar_valor = {
            'estructura': 'repite',
            'argumento': None,
            'cola': []
        }

        self.avanza_token()
        retornar_valor['argumento'] = self.expresion_entera(lista_variables)

        if self.token_actual != 'veces':
            raise KarelException("Se esperaba la palabra 'veces', '%s' no es válido"%self.token_actual)

        self.avanza_token()
        retornar_valor['cola'] = self.expresion(lista_variables, c_funcion, True)

        return retornar_valor

    def expresion_si(self, lista_variables, c_funcion, c_bucle):
        retornar_valor = {
            'estructura': 'si',
            'argumento': None,
            'cola': []
        }

        self.avanza_token()

        retornar_valor['argumento'] = self.termino(lista_variables)

        if self.token_actual != 'entonces':
            raise KarelException("Se esperaba 'entonces'")

        self.avanza_token()

        retornar_valor['cola'] = self.expresion(lista_variables, c_funcion, c_bucle)

        if self.token_actual == 'sino':
            retornar_valor.update({'sino-cola': []})
            self.avanza_token()
            retornar_valor['sino-cola'] = self.expresion(lista_variables, c_funcion, c_bucle)

        return retornar_valor

    def funcion_booleana(self):
        retornar_valor = ""

        if self.token_actual in self.condiciones:
            retornar_valor = self.token_actual
            self.avanza_token()
        else:
            raise KarelException("Se esperaba una condición como 'frente-libre', '%s' no es una condición"%self.token_actual)

        return retornar_valor

  
    def verificar_sintaxis (self):
        if self.token_actual == 'iniciar-programa':
            if self.avanza_token():
                self.bloque()
                if self.token_actual != 'finalizar-programa':
                    raise KarelException("Se esperaba 'finalizar-programa' al final del codigo")
            else:
                for funcion in self.llamadas_funciones:
                        if self.funciones.has_key(funcion):
                            if len(self.funciones[funcion]) != self.llamadas_funciones[funcion]:
                                raise KarelException("La funcion '%s' no se llama con la misma cantidad de parámetros que como se definió"%funcion)
                        else:
                            raise KarelException("La función '%s' es llamada pero no fue declarada"%funcion)
                else:
                    raise KarelException('%s no es un identificador valido'%self.token_actual)

        if self.strict and (not self.tiene_apagate):
            raise KarelException("Tu código no tiene 'apagate', esto no es permitido en el modo estricto")
if __name__ == "__main__":
    
    from pprint import pprint
    from time import time
    inicio = time()
    fil = sys.argv[0]
    grammar = kgrammar(flujo=open('codigo.txt'), archivo='codigo.txt')
    pprint(grammar.arbol)
    
   for i in xrange(len(grammar.lista_programa)):
        print i,grammar.lista_programa[i]     
    fin = time()
    print "time: ", fin-inicio
