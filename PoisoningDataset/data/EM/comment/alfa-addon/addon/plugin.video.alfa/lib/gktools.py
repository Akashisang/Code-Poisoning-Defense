# -*- coding: utf-8 -*-

"""
gktools son un conjunto de funciones para ayudar a resolver enlaces a videos con "protección GK".
Lo de protección gk dudo que exista, le he llamado así pq los primeros ejemplos vistos se eran gkpluginsphp y gkpedia.

Características "GK" :
- Utiliza una cookie __cfduid
- Calcula un token criptográfico en función de un texto y una clave
- El texto se saca del html (por ejemplo de meta name="google-site-verification", pero puede ser más complejo)
- La clave para encriptar se calcula en js ofuscados que carga el html
- Se llama a otra url con una serie de parámetros, como el token, y de allí se obtienen los videos finales.

Howto:
1- descargar página
2- extraer datos y calcular los necesarios
3- descargar segunda página con el token calculado
4- extraer videos

El paso 2 es con diferencia el más variable y depende mucho de cada web/servidor!
Desofuscando los js se pueden ver los datos propios que necesita cada uno
(el texto a encriptar, la clave a usar, la url dónde hay que llamar y los parámetros)

Ver ejemplos en el código de los canales animeyt y pelispedia


Created for Alfa-addon by Alfa Developers Team 2018
"""
