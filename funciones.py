import time
from io import open
import rrdtool
import os
from pysnmp.hlapi import *
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import threading
from pdf_mail import sendpdf

def agregarElemento (lista,comunidad,direccion,version,puerto):
    if(lista[0]==0):
        lista.pop()
    lista.extend([direccion,comunidad,version,puerto])

def guardarAgentes(lista):
    try:
        archivo = open("agentes.txt", "w")
        i = 0
        while i < len(lista):
            a = lista[i]
            archivo.write(a + "\n")
            i += 1
        archivo.close()
        print("\nAgentes guardados\n")
    except:
        print("No fue posible guardar los agentes")

def leerAgentes(lista):
    try:
        archivo = open("agentes.txt", "r")
        lista = archivo.read().split("\n")
        lista.pop()
        archivo.close()
        print(lista, "Numero de agentes monitorizados:",len(lista)/4)
        return lista
    except:
        print("No se pudo leer los agentes")

def imprimirLista (lista):
    print(lista[:])

def eliminarAgente (lista,direccion):
    try:
        dex=lista.index(direccion)
        dex2=dex+3
        i=int(dex)
        i=(i/4)+1
        try:
            archivo="agente"+str(int(i))
            os.remove("/home/mint2/Documentos/Practica_2/RRD/"+archivo+".rrd")
            os.remove("/home/mint2/Documentos/Practica_2/RRD/"+archivo + ".xml")
            os.remove("/home/mint2/Documentos/Practica_2/IMG/"+archivo + "CPU.png")
            os.remove("/home/mint2/Documentos/Practica_2/IMG/"+archivo + "DSK.png")
            os.remove("/home/mint2/Documentos/Practica_2/IMG/"+archivo + "RAM.png")
            os.remove("Reporte de agentes.pdf")
        except:
            print("No hay archivos")
        while (dex<=dex2):
            lista.pop(dex2)
            dex2-=1
    except:
       print("No hay agentes")

def consultaSNMP(comunidad,host,oid,puerto):
    errorIndication, errorStatus, errorIndex, varBinds = next(
        getCmd(SnmpEngine(),
               CommunityData(comunidad),
               UdpTransportTarget((host, puerto)),
               ContextData(),
               ObjectType(ObjectIdentity(oid))))

    if errorIndication:
        resultado=errorIndication
    elif errorStatus:
        print('%s at %s' % (errorStatus.prettyPrint(),errorIndex and varBinds[int(errorIndex) - 1][0] or '?'))
    else:
        for varBind in varBinds:
            varB=(' = '.join([x.prettyPrint() for x in varBind]))
            resultado= varB.split()[2]
    return resultado

def consultaSNMP2(comunidad,host,oid,puerto):
    errorIndication, errorStatus, errorIndex, varBinds = next(
        getCmd(SnmpEngine(),
               CommunityData(comunidad),
               UdpTransportTarget((host, puerto)),
               ContextData(),
               ObjectType(ObjectIdentity(oid))))

    if errorIndication:
        resultado=errorIndication
    elif errorStatus:
        print('%s at %s' % (errorStatus.prettyPrint(),errorIndex and varBinds[int(errorIndex) - 1][0] or '?'))
    else:
        for varBind in varBinds:
            varB=(' = '.join([x.prettyPrint() for x in varBind]))
            resultado= varB.split()[14]
    return resultado

def estadoAgente (lista):
    tamaño=int(len(lista))/4
    print("Número de agentes monitorizados",tamaño)
    i=0
    j=0
    while (i<tamaño):
        resultado=consultaSNMP(lista[j+1],lista[j],'1.3.6.1.2.1.1.1.0',int(lista[j+3]))
        if(str(resultado)=="No SNMP response received before timeout"):
            print("Estado del agente",i+1,": down")
        else:
            print("Estado del agente",i+1,": up")
            resultado=consultaSNMP(lista[j+1],lista[j],'1.3.6.1.2.1.2.1.0',lista[j+3])
            print("El número de interfaces de red del agente",i+1,"son:", resultado)
        i+=1
        j+=4

def createRRD(nombre):
    nombre+=".rrd"
    ret = rrdtool.create("/home/mint2/Documentos/Practica_2/RRD/"+nombre,
                         "--start", 'N',
                         "--step", '60',
                         "DS:CPUload:GAUGE:600:U:U",
                         "DS:RAMload:GAUGE:600:U:U",
                         "DS:DSKload:GAUGE:600:U:U",
                         "RRA:AVERAGE:0.5:1:24",
                         "RRA:AVERAGE:0.5:1:24",
                         "RRA:AVERAGE:0.5:1:24")

    if ret:
        print(rrdtool.error())
    else :
        print("Creación satisfactoria")

def updateRRD (lista, agente, nombre, tiempo):
    timeout = time.time() + tiempo
    timeinit= time.time()
    xml=nombre+".xml"
    nombre+=".rrd"
    rrdpath = '/home/mint2/Documentos/Practica_2/RRD/'
    carga_CPU = 0
    carga_RAM=0
    carga_DSK=0
    j=(agente-1)*4
    if lista[j+2]=="windows":
        while 1:
            if time.time() > timeout:
                break
            carga_CPU = int(consultaSNMP(lista[j + 1], lista[j], '1.3.6.1.2.1.25.3.3.1.2.6', int(lista[j + 3])))
            carga_RAM = int(consultaSNMP(lista[j + 1], lista[j], '1.3.6.1.2.1.25.2.3.1.6.3', int(lista[j + 3])))
            carga_DSK = int(consultaSNMP(lista[j + 1], lista[j], '1.3.6.1.2.1.25.2.3.1.6.1', int(lista[j + 3])))
            valor = "N:" + str(carga_CPU) + ":" + str(carga_RAM) + ":" + str(carga_DSK)
            #print(valor)
            rrdtool.update(rrdpath + nombre, valor)
            rrdtool.dump(rrdpath + nombre, rrdpath + xml)
            time.sleep(3)
            while timeinit+120 <= time.time():
                if carga_CPU > 45:
                    creacionGraphU(lista, agente, tiempo)
                    generarPDF(lista)
                    enviarCorreo("Sobrepasa Umbral línea base 1 CPU")
                    print("Sobrepasa Umbral línea base")
                    timeinit=time.time()+tiempo
                    if carga_CPU > 85:
                        enviarCorreo("Sobrepasa Umbral línea base 2 CPU")
                        print("Sobrepasa Umbral línea base")
                        if carga_CPU >= 97:
                            enviarCorreo("Sobrepasa Umbral línea base 3 CPU")
                            print("Sobrepasa Umbral línea base")
                time.sleep(3)
                if carga_RAM > 97305:
                    creacionGraphU(lista, agente, tiempo)
                    generarPDF(lista)
                    enviarCorreo("Sobrepasa Umbral línea base 1 RAM")
                    print("Sobrepasa Umbral línea base")
                    timeinit = time.time()+tiempo
                    if carga_RAM > 136226:
                        enviarCorreo("Sobrepasa Umbral línea base 2 RAM")
                        print("Sobrepasa Umbral línea base")
                        if carga_RAM >= 175879:
                            enviarCorreo("Sobrepasa Umbral línea base 3 RAM")
                            print("Sobrepasa Umbral línea base")
                time.sleep(3)
                if carga_DSK > 50697611:
                    creacionGraphU(lista, agente, tiempo)
                    generarPDF(lista)
                    enviarCorreo("Sobrepasa Umbral línea base 1 DSK")
                    print("Sobrepasa Umbral línea base")
                    timeinit = time.time()+tiempo
                    if carga_DSK > 58497243:
                        enviarCorreo("Sobrepasa Umbral línea base 2 DSK")
                        print("Sobrepasa Umbral línea base")
                        if carga_DSK >= 70096692:
                            enviarCorreo("Sobrepasa Umbral línea base 3 DSK")
                            print("Sobrepasa Umbral línea base")
            time.sleep(1)
    else:
        while 1:
            if time.time() > timeout:
                break
            carga_CPU = int(consultaSNMP(lista[j + 1], lista[j], '1.3.6.1.2.1.25.3.3.1.2.196608', int(lista[j + 3])))
            carga_RAM = int(consultaSNMP(lista[j + 1], lista[j], '1.3.6.1.4.1.2021.4.6.0', int(lista[j + 3])))
            carga_DSK = int(consultaSNMP(lista[j + 1], lista[j], '1.3.6.1.4.1.2021.9.1.9.1', int(lista[j + 3])))
            valor = "N:" + str(carga_CPU) + ":" + str(carga_RAM) + ":" + str(carga_DSK)
            #print(valor)
            rrdtool.update(rrdpath + nombre, valor)
            rrdtool.dump(rrdpath + nombre, rrdpath + xml)
            time.sleep(3)
            if timeinit+120 <= time.time():
                if carga_CPU > 45:
                    creacionGraphU(lista, agente, tiempo)
                    generarPDF(lista)
                    enviarCorreo("Sobrepasa Umbral línea base 1 CPU")
                    print("Sobrepasa Umbral línea base")
                    timeinit = time.time()+tiempo
                    if carga_CPU > 85:
                        enviarCorreo("Sobrepasa Umbral línea base 2 CPU")
                        print("Sobrepasa Umbral línea base")
                        time.sleep(8)
                        if carga_CPU >= 97:
                            enviarCorreo("Sobrepasa Umbral línea base 3 CPU")
                            print("Sobrepasa Umbral línea base")
                time.sleep(3)
                if carga_RAM < 1017726:
                    creacionGraphU(lista, agente, tiempo)
                    generarPDF(lista)
                    enviarCorreo("Sobrepasa Umbral línea base 1 RAM")
                    print("Sobrepasa Umbral línea base")
                    timeinit = time.time() + tiempo
                    if carga_RAM < 508863:
                        enviarCorreo("Sobrepasa Umbral línea base 2 RAM")
                        print("Sobrepasa Umbral línea base")
                        if carga_RAM < 122127:
                            enviarCorreo("Sobrepasa Umbral línea base 3 RAM")
                            print("Sobrepasa Umbral línea base")
                time.sleep(3)
                if carga_DSK > 65:
                    creacionGraphU(lista, agente, tiempo)
                    generarPDF(lista)
                    enviarCorreo("Sobrepasa Umbral línea base 1 DSK")
                    print("Sobrepasa Umbral línea base")
                    timeinit = time.time()+tiempo
                    if carga_DSK > 75:
                        enviarCorreo("Sobrepasa Umbral línea base 2 DSK")
                        print("Sobrepasa Umbral línea base")
                        if carga_DSK >= 90:
                            enviarCorreo("Sobrepasa Umbral línea base 3 DSK")
                            print("Sobrepasa Umbral línea base")
            time.sleep(1)

def graphRRD(nombre, tiempo, agente, lista):
    rrdpath = '/home/mint2/Documentos/Practica_2/RRD/'
    imgpath = '/home/mint2/Documentos/Practica_2/IMG/'
    j=(agente-1)*4
    ultima_lectura = int(rrdtool.last(rrdpath + nombre +".rrd"))
    tiempo_final = ultima_lectura
    tiempo_inicial = tiempo_final - tiempo
    if lista[j+2]=="linux":
        carga_RAM = int(consultaSNMP(lista[j + 1], lista[j], '1.3.6.1.4.1.2021.4.5.0', int(lista[j + 3])))
        ret = rrdtool.graphv(imgpath + nombre + "CPU.png",
                             "--start", str(tiempo_inicial),
                             "--end", str(tiempo_final),
                             "--vertical-label=Cpu load",
                             '--lower-limit', '0',
                             '--upper-limit', '100',
                             "--title=Uso del CPU del agente Usando SNMP y RRDtools \n Detección de umbrales",

                             "DEF:cargaCPU=" + rrdpath + nombre + ".rrd:CPUload:AVERAGE",

                             "VDEF:cargaMAX=cargaCPU,MAXIMUM",
                             "VDEF:cargaMIN=cargaCPU,MINIMUM",
                             "VDEF:cargaSTDEV=cargaCPU,STDEV",
                             "VDEF:cargaLAST=cargaCPU,LAST",

                             "CDEF:umbral5=cargaCPU,97,LT,0,cargaCPU,IF",
                             "AREA:cargaCPU#00FF00:Carga del CPU",
                             "AREA:umbral5#FF9F00:Carga CPU mayor que 97%",
                             "HRULE:97#FF0000:Umbral 3 - 97%",
                             "HRULE:85#EE0000:Umbral 2 - 85%",
                             "HRULE:45#BB0000:Umbral 1 - 45%",

                             "PRINT:cargaLAST:%6.2lf",
                             "GPRINT:cargaMIN:%6.2lf %SMIN",
                             "GPRINT:cargaMAX:%6.2lf %SMAX",
                             "GPRINT:cargaLAST:%6.2lf %SLAST")

        ret = rrdtool.graphv(imgpath + nombre + "RAM.png",
                             "--start", str(tiempo_inicial),
                             "--end", str(tiempo_final),
                             "--vertical-label=Cpu load",
                             '--lower-limit', '0',
                             '--upper-limit', '100',
                             "--title=Uso de RAM del agente Usando SNMP y RRDtools \n Detección de umbrales",

                             "DEF:cargaRAM=" + rrdpath + nombre + ".rrd:RAMload:AVERAGE",

                             "CDEF:porcentajeRAM=cargaRAM,1048576,/,"+str((carga_RAM/1048576))+",2,REV,-,100,*,"+str((carga_RAM/1048576))+",/",
                             "VDEF:cargaMAX=porcentajeRAM,MAXIMUM",
                             "VDEF:cargaMIN=porcentajeRAM,MINIMUM",
                             "VDEF:cargaSTDEV=porcentajeRAM,STDEV",
                             "VDEF:cargaLAST=porcentajeRAM,LAST",

                             "CDEF:umbral5=porcentajeRAM,95,LT,0,porcentajeRAM,IF",
                             "AREA:porcentajeRAM#00FF00:Carga de RAM",
                             "AREA:umbral5#FF9F00:Carga RAM mayor que 95%",
                             "HRULE:95#FF0000:Umbral 3 - 95%",
                             "HRULE:70#EE0000:Umbral 2 - 70%",
                             "HRULE:50#BB0000:Umbral 1 - 50%",

                             "PRINT:cargaLAST:%6.2lf",
                             "GPRINT:cargaMIN:%6.2lf %SMIN",
                             "GPRINT:cargaMAX:%6.2lf %SMAX",
                             "GPRINT:cargaLAST:%6.2lf %SLAST")
        ret = rrdtool.graphv(imgpath + nombre + "DSK.png",
                             "--start", str(tiempo_inicial),
                             "--end", str(tiempo_final),
                             "--vertical-label=DSK load",
                             '--lower-limit', '0',
                             '--upper-limit', '100',
                             "--title=Uso del Disco Duro del agente Usando SNMP y RRDtools \n Detección de umbrales",

                             "DEF:cargaDSK=" + rrdpath + nombre + ".rrd:DSKload:AVERAGE",

                             "VDEF:cargaMAX=cargaDSK,MAXIMUM",
                             "VDEF:cargaMIN=cargaDSK,MINIMUM",
                             "VDEF:cargaSTDEV=cargaDSK,STDEV",
                             "VDEF:cargaLAST=cargaDSK,LAST",

                             "CDEF:umbral5=cargaDSK,100,LT,0,cargaDSK,IF",
                             "AREA:cargaDSK#00FF00:Carga del DISCO",
                             "AREA:umbral5#FF9F00:Carga DISCO mayor que 90%",
                             "HRULE:90#FF0000:Umbral 3 - 90%",
                             "HRULE:75#EE0000:Umbral 2 - 75%",
                             "HRULE:65#BB0000:Umbral 1 - 65%",

                             "PRINT:cargaLAST:%6.2lf",
                             "GPRINT:cargaMIN:%6.2lf %SMIN",
                             "GPRINT:cargaMAX:%6.2lf %SMAX",
                             "GPRINT:cargaLAST:%6.2lf %SLAST")
    else:
        carga_RAM = int(consultaSNMP(lista[j + 1], lista[j], '1.3.6.1.2.1.25.2.3.1.5.3', int(lista[j + 3])))
        carga_DSK = int(consultaSNMP(lista[j + 1], lista[j], '1.3.6.1.2.1.25.2.3.1.5.1', int(lista[j + 3])))
        ret = rrdtool.graphv(imgpath + nombre + "CPU.png",
                             "--start", str(tiempo_inicial),
                             "--end", str(tiempo_final),
                             "--vertical-label=Cpu load",
                             '--lower-limit', '0',
                             '--upper-limit', '100',
                             "--title=Uso del CPU del agente Usando SNMP y RRDtools \n Detección de umbrales",

                             "DEF:cargaCPU=" + rrdpath + nombre + ".rrd:CPUload:AVERAGE",

                             "VDEF:cargaMAX=cargaCPU,MAXIMUM",
                             "VDEF:cargaMIN=cargaCPU,MINIMUM",
                             "VDEF:cargaSTDEV=cargaCPU,STDEV",
                             "VDEF:cargaLAST=cargaCPU,LAST",

                             "CDEF:umbral5=cargaCPU,97,LT,0,cargaCPU,IF",
                             "AREA:cargaCPU#00FF00:Carga del CPU",
                             "AREA:umbral5#FF9F00:Carga CPU mayor que 97%",
                             "HRULE:97#FF0000:Umbral 3 - 97%",
                             "HRULE:85#EE0000:Umbral 2 - 85%",
                             "HRULE:45#BB0000:Umbral 1 - 45%",

                             "PRINT:cargaLAST:%6.2lf",
                             "GPRINT:cargaMIN:%6.2lf %SMIN",
                             "GPRINT:cargaMAX:%6.2lf %SMAX",
                             "GPRINT:cargaLAST:%6.2lf %SLAST")

        ret = rrdtool.graphv(imgpath + nombre + "RAM.png",
                             "--start", str(tiempo_inicial),
                             "--end", str(tiempo_final),
                             "--vertical-label=Cpu load",
                             '--lower-limit', '0',
                             '--upper-limit', '100',
                             "--title=Uso de RAM del agente Usando SNMP y RRDtools \n Detección de umbrales",

                             "DEF:cargaRAM=" + rrdpath + nombre + ".rrd:RAMload:AVERAGE",

                             "CDEF:porcentajeRAM=cargaRAM,100,*,"+str(carga_RAM)+",/",
                             "VDEF:cargaMAX=porcentajeRAM,MAXIMUM",
                             "VDEF:cargaMIN=porcentajeRAM,MINIMUM",
                             "VDEF:cargaSTDEV=porcentajeRAM,STDEV",
                             "VDEF:cargaLAST=porcentajeRAM,LAST",

                             "CDEF:umbral5=porcentajeRAM,95,LT,0,porcentajeRAM,IF",
                             "AREA:porcentajeRAM#00FF00:Carga de RAM",
                             "AREA:umbral5#FF9F00:Carga RAM mayor que 95%",
                             "HRULE:95#FF0000:Umbral 3 - 95%",
                             "HRULE:70#EE0000:Umbral 2 - 70%",
                             "HRULE:50#BB0000:Umbral 1 - 50%",

                             "PRINT:cargaLAST:%6.2lf",
                             "GPRINT:cargaMIN:%6.2lf %SMIN",
                             "GPRINT:cargaMAX:%6.2lf %SMAX",
                             "GPRINT:cargaLAST:%6.2lf %SLAST")

        ret = rrdtool.graphv(imgpath + nombre + "DSK.png",
                             "--start", str(tiempo_inicial),
                             "--end", str(tiempo_final),
                             "--vertical-label=DSK load",
                             '--lower-limit', '0',
                             '--upper-limit', '100',
                             "--title=Uso del Disco Duro del agente Usando SNMP y RRDtools \n Detección de umbrales",

                             "DEF:cargaDSK=" + rrdpath + nombre + ".rrd:DSKload:AVERAGE",

                             "CDEF:porcentajeDSK=cargaDSK,100,*,"+str(carga_DSK)+",/",
                             "VDEF:cargaMAX=porcentajeDSK,MAXIMUM",
                             "VDEF:cargaMIN=porcentajeDSK,MINIMUM",
                             "VDEF:cargaSTDEV=porcentajeDSK,STDEV",
                             "VDEF:cargaLAST=porcentajeDSK,LAST",

                             "CDEF:umbral5=porcentajeDSK,90,LT,0,porcentajeDSK,IF",
                             "AREA:porcentajeDSK#00FF00:Carga del DISCO",
                             "AREA:umbral5#FF9F00:Carga DISCO mayor que 90%",
                             "HRULE:90#FF0000:Umbral 3 - 90%",
                             "HRULE:75#EE0000:Umbral 2 - 75%",
                             "HRULE:65#BB0000:Umbral 1 - 65%",

                             "PRINT:cargaLAST:%6.2lf",
                             "GPRINT:cargaMIN:%6.2lf %SMIN",
                             "GPRINT:cargaMAX:%6.2lf %SMAX",
                             "GPRINT:cargaLAST:%6.2lf %SLAST")

def enviarCorreo(subject):
    k= sendpdf("jonathanvillaloboscecyt2@gmail.com",
               "tanibet.escom@gmail.com",
               "jonylobo2",
               subject,"Reporte de linea de base- Villalobos Aceves Jonathan Jesus 4CM13.",
               "Reporte de agentes",
               "/home/mint2/Documentos/Practica_2")
    k.email_send()


def creacion(lista):
    agente = int(input("Indique el número del agente: "))
    nombre="agente"+str(agente)
    createRRD(nombre)
    tiempo=int(input("Tiempo de ejecuci+on de update en segundos: "))
    thread = threading.Thread(name="hilo1", target=updateRRD, args=(lista,agente,nombre,tiempo,))
    thread.start()

def creacionGraph (lista):
    agente = int(input("Ingresa el numero de agente: "))
    nombre="agente"+str(agente)
    tiempo = int(input("Ingresa el tiempo utlizado en segundos: "))
    graphRRD(nombre, tiempo,agente,lista)
    print("Operación exitosa\n\n")

def creacionGraphU (lista, ag, t):
    agente = ag
    nombre="agente"+str(agente)
    tiempo = int(t)
    graphRRD(nombre, tiempo,agente,lista)
    print("Operación exitosa\n\n")

def generarPDF (lista):
    j=0
    c=canvas.Canvas("Reporte de agentes.pdf", pagesize=A4)
    h=A4
    i=0
    path="/home/mint2/Documentos/Practica_2/IMG/"
    while i < len(lista)/4:
        print(lista[j + 2])
        k=400*i
        if lista[j+2] == "windows":
            c.drawImage("Windows.jpeg", 20, h[1] -60 - k, width=50, height=50)
            text = c.beginText(50, h[1] - 80-k)
            text.textLines(
                "\n\n\nNombre: " + str(consultaSNMP(lista[j + 1], lista[j], '1.3.6.1.2.1.1.5.0', lista[j + 3])) + "   "
                + "Version: " + str(consultaSNMP(lista[j + 1], lista[j], '1.3.6.1.2.1.1.2.0', lista[j + 3])) + "    "
                + "   SO: " + str(consultaSNMP2(lista[j + 1], lista[j], '1.3.6.1.2.1.1.1.0', lista[j + 3])) + "\n"
                + "Ubicacion: " + str(consultaSNMP(lista[j + 1], lista[j], '1.3.6.1.2.1.1.6.0', lista[j + 3])) + "\n"
                + "Puerto: " + str(lista[j + 3]) + " Tiempo de Actividad: " + str(
                    consultaSNMP(lista[j + 1], lista[j], '1.3.6.1.2.1.1.3.0', lista[j + 3])) + "\n"
                + "Comunidad: " + str(lista[j + 1]) + " IP: " + str(lista[j]))
            c.drawText(text)
            c.drawImage(path+"agente" + str(i+1) + "CPU.png", 50, h[1] - 270-k, width=248, height=143)
            c.drawImage(path+"agente" + str(i+1) + "DSK.png", 310, h[1] - 270-k, width=248, height=143)
            c.drawImage(path+"agente" + str(i+1) + "RAM.png", 50, h[1] - 410-k, width=248, height=143)
            i+=1
            j+=4
        else:
            c.drawImage("mint.png", 20, h[1] - 60 - k, width=50, height=50)
            text = c.beginText(50, h[1] - 80 - k)
            text.textLines(
                "\n\n\nNombre: " + str(consultaSNMP(lista[j + 1], lista[j], '1.3.6.1.2.1.1.5.0', lista[j + 3])) + "   "
                + "Version: " + str(consultaSNMP(lista[j + 1], lista[j], '1.3.6.1.2.1.1.2.0', lista[j + 3])) + "    "
                + "   SO: " + str(consultaSNMP(lista[j + 1], lista[j], '1.3.6.1.2.1.1.1.0', lista[j + 3])) + "\n"
                + "Ubicacion: " + str(consultaSNMP(lista[j + 1], lista[j], '1.3.6.1.2.1.1.6.0', lista[j + 3])) + "\n"
                + "Puerto: " + str(lista[j + 3]) + " Tiempo de Actividad: " + str(
                    consultaSNMP(lista[j + 1], lista[j], '1.3.6.1.2.1.1.3.0', lista[j + 3])) + "\n"
                + "Comunidad: " + str(lista[j + 1]) + " IP: " + str(lista[j]))
            c.drawText(text)
            c.drawImage(path+"agente" + str(i + 1) + "CPU.png", 50, h[1] - 270 - k, width=248, height=143)
            c.drawImage(path+"agente" + str(i + 1) + "DSK.png", 310, h[1] - 270 - k, width=248, height=143)
            c.drawImage(path+"agente" + str(i + 1) + "RAM.png", 50, h[1] - 410 - k, width=248, height=143)
            i+=1
            j+=4
    c.showPage()
    c.save()

def reporte(lista):
    generarPDF(lista)
