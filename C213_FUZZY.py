
import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as sistema
import random
import time

from paho.mqtt import client as mqtt_client

broker = 'broker.emqx.io'
port = 1883
client_id = f'python-mqtt-{random.randint(0, 1000)}'
sp = 36


def connect_mqtt():
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker!")
        else:
            print("Failed to connect, return code %d\n", rc)

    client = mqtt_client.Client(client_id)
    client.on_connect = on_connect
    client.connect(broker, port)
    client.subscribe("C213/payload")
    return client


def calculafuzzy(erro_at, delta_erro):
    # Definição das variáveis envolvidas no sistema
    # Antecedente (Var. de Entrada):
    erro = sistema.Antecedent(np.arange(-35, 35, 1), 'erro')
    varerro = sistema.Antecedent(np.arange(-2, 2, 0.1), 'varerro')

    # Consequente (Var. de Saída):
    resistencia = sistema.Consequent(np.arange(0, 101, 1), 'resistencia')
    # Erro:
    erro['MN'] = fuzz.trapmf(erro.universe, [-35, -35, -2, -1])
    erro['PN'] = fuzz.trimf(erro.universe, [-2, -1, 0])
    erro['Z'] = fuzz.trimf(erro.universe, [-1, 0, 1])
    erro['PP'] = fuzz.trimf(erro.universe, [0, 1, 2])
    erro['MP'] = fuzz.trapmf(erro.universe, [1, 2, 35, 35])

    # VarErro
    varerro['MN'] = fuzz.trapmf(varerro.universe, [-2, -2, -0.2, -0.1])
    varerro['PN'] = fuzz.trimf(varerro.universe, [-0.2, -0.1, 0])
    varerro['Z'] = fuzz.trimf(varerro.universe, [-0.1, 0, 0.1])
    varerro['PP'] = fuzz.trimf(varerro.universe, [0, 0.1, 0.2])
    varerro['MP'] = fuzz.trapmf(varerro.universe, [0.1, 0.2, 2, 2])

    # resistencia:
    resistencia['MB'] = fuzz.trimf(resistencia.universe, [0, 0, 25])
    resistencia['B'] = fuzz.trimf(resistencia.universe, [0, 25, 50])
    resistencia['N'] = fuzz.trimf(resistencia.universe, [25, 50, 75])
    resistencia['A'] = fuzz.trimf(resistencia.universe, [50, 75, 100])
    resistencia['MA'] = fuzz.trimf(resistencia.universe, [75, 100, 100])

    # DEFINIÇÃO DA BASE DE REGRAS:
    # MN = MUITO NEGATIVA
    # N = NEGATIVA
    # MP = MUITO POSITIVA
    # P = POSITIVO
    # Z = ZERO
    regra1 = sistema.Rule(erro['MN'] & varerro['MN'], resistencia['MA'])
    regra2 = sistema.Rule(erro['MN'] & varerro['PN'], resistencia['MA'])
    regra3 = sistema.Rule(erro['MN'] & varerro['Z'], resistencia['MA'])
    regra4 = sistema.Rule(erro['MN'] & varerro['PP'], resistencia['A'])
    regra5 = sistema.Rule(erro['MN'] & varerro['MP'], resistencia['N'])
    regra6 = sistema.Rule(erro['PN'] & varerro['MN'], resistencia['MA'])
    regra7 = sistema.Rule(erro['PN'] & varerro['PN'], resistencia['A'])
    regra8 = sistema.Rule(erro['PN'] & varerro['Z'], resistencia['A'])
    regra9 = sistema.Rule(erro['PN'] & varerro['PP'], resistencia['A'])
    regra10 = sistema.Rule(erro['PN'] & varerro['MP'], resistencia['N'])
    regra11 = sistema.Rule(erro['Z'] & varerro['MN'], resistencia['A'])
    regra12 = sistema.Rule(erro['Z'] & varerro['PN'], resistencia['A'])
    regra13 = sistema.Rule(erro['Z'] & varerro['Z'], resistencia['N'])
    regra14 = sistema.Rule(erro['Z'] & varerro['PP'], resistencia['N'])
    regra15 = sistema.Rule(erro['Z'] & varerro['MP'], resistencia['B'])
    regra16 = sistema.Rule(erro['PP'] & varerro['MN'], resistencia['N'])
    regra17 = sistema.Rule(erro['PP'] & varerro['PN'], resistencia['B'])
    regra18 = sistema.Rule(erro['PP'] & varerro['Z'], resistencia['B'])
    regra19 = sistema.Rule(erro['PP'] & varerro['PP'], resistencia['B'])
    regra20 = sistema.Rule(erro['PP'] & varerro['MP'], resistencia['MB'])
    regra21 = sistema.Rule(erro['MP'] & varerro['MN'], resistencia['N'])
    regra22 = sistema.Rule(erro['MP'] & varerro['PN'], resistencia['B'])
    regra23 = sistema.Rule(erro['MP'] & varerro['Z'], resistencia['MB'])
    regra24 = sistema.Rule(erro['MP'] & varerro['PP'], resistencia['MB'])
    regra25 = sistema.Rule(erro['MP'] & varerro['MP'], resistencia['MB'])

    # Inclusão das regras no sistema definido
    resistencia_sistema = sistema.ControlSystem(
        [regra1, regra2, regra3, regra4, regra5, regra6, regra7, regra8, regra9, regra10, regra11, regra12, regra13,
         regra14, regra15, regra16, regra17, regra18, regra19, regra20, regra21, regra22, regra23, regra24, regra25])

    # Definição do módulo de inferência
    controlador = sistema.ControlSystemSimulation(resistencia_sistema)

    controlador.input['erro'] = erro_at
    controlador.input['varerro'] = delta_erro
    controlador.compute()
    return controlador.output['resistencia']


def on_message(client, userdata, message):
    global sp
    new_setpoint = str(message.payload)
    temp = new_setpoint.replace('b', '').replace("'", '')
    print("Escolha da temperatura: " + temp)
    sp = int(temp)
    print()


def publish(client):
    pv = 36
    erro_at = 0
    while True:
        client.on_message = on_message
        erro_ant = erro_at
        erro_at = pv - sp
        delta_erro = erro_at - erro_ant
        pot = calculafuzzy(erro_at, delta_erro)
        print("Erro atual: {}".format(round(erro_at, 2)))
        print("Erro anterior: {}".format(round(erro_ant, 2)))
        print("Delta erro: {}".format(round(delta_erro, 2)))
        print("Potencia: {}".format(round(pot, 2)))
        print("Set point: {}".format(round(sp, 2)))
        print("Temperatura: {}".format(round(pv, 2)))

        client

        for i in range(11):
            pv = (pv * 0.9954) + (pot * 0.002763)
            time.sleep(1)


def run():
    client = connect_mqtt()
    client.loop_start()
    publish(client)


# Chama a funcao Run responsável pela execução do programa
run()

