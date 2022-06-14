import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as sistema
import random
import time

from paho.mqtt import client as mqtt_client


class Fuzzy:
    def __init__(self):
        self.temp = None
        self.pv = None
        self.erro_atual = None
        self.erro_anterior = None
        self.setpoint_changed = 36
        self.broker = 'broker.emqx.io'
        self.port = 1883
        self.client_id = f'python-mqtt-{random.randint(0, 1000)}'

    def connect_mqtt(self):
        def on_connect(client, userdata, flags, rc):
            """
            :param rc:
            :param flags:
            :param userdata:
            :type client: object
            """
            if rc == 0:
                print("Conectado")
            else:
                print("Error code %d\n", rc)

        client = mqtt_client.Client(self.client_id)
        client.on_connect = on_connect
        client.connect(self.broker, self.port)
        client.subscribe("C213/payload")
        return client

    def calculafuzzy(self, erro_atual, delta_erro):
        """
        :param delta_erro:
        :type erro_atual: object
        """
        # Definição das variáveis envolvidas no sistema
        # Antecedente (Var. de Entrada):
        erro = sistema.Antecedent(np.arange(-28, 13, 1), 'erro')
        varerro = sistema.Antecedent(np.arange(-2, 2, 0.1), 'varerro')

        # Consequente (Var. de Saída):
        resistencia = sistema.Consequent(np.arange(0, 101, 1), 'resistencia')
        # Erro:
        erro['MN'] = fuzz.trapmf(erro.universe, [-28, -28, -2, -1])
        erro['PN'] = fuzz.trimf(erro.universe, [-2, -1, 0])
        erro['Z'] = fuzz.trimf(erro.universe, [-1, 0, 1])
        erro['PP'] = fuzz.trimf(erro.universe, [0, 1, 2])
        erro['MP'] = fuzz.trapmf(erro.universe, [1, 2, 13, 13])

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
             regra14, regra15, regra16, regra17, regra18, regra19, regra20, regra21, regra22, regra23, regra24,
             regra25])

        # Definição do módulo de inferência
        controlador = sistema.ControlSystemSimulation(resistencia_sistema)

        controlador.input['erro'] = erro_atual
        controlador.input['varerro'] = delta_erro
        controlador.compute()
        return controlador.output['resistencia']

    def on_message(self, client, userdata, message):
        """
        :param message:
        :param userdata:
        :type client: object
        """
        new_setpoint = str(message.payload)
        self.temp = new_setpoint.replace('b', '').replace("'", '')
        print("Temperatura setada: " + self.temp)
        self.setpoint_changed = int(self.temp)

    def publish(self, client):
        """
        :type client: object
        """
        self.pv = 36
        self.erro_atual = 0
        while True:
            client.on_message = self.on_message
            self.erro_anterior = self.erro_atual
            self.erro_atual = self.pv - self.setpoint_changed
            delta_erro = self.erro_atual - self.erro_anterior
            res = self.calculafuzzy(self.erro_atual, delta_erro)
            print(" ----------------------------")
            print("|  Tabela de Resposta        |")
            print(f"| Erro anterior: {self.erro_anterior:.3f}       |")
            print(f"| Erro atual: {self.erro_atual:.3f}          |")
            print(f"| Resistencia Atual: {res:.3f}     |")
            print(f"| Delta Erro Atual: {delta_erro:.3f}    |")
            print(f"| Set Point Atual: {self.setpoint_changed:.3f}    |")
            print(f"| Temperatura Atual: {self.pv:.3f}  |")
            print(" ----------------------------")

            i = 0
            while (i < 10): # mudar a temperatura de tempo em tempo criando uma resistencia nova sem isso a
                # variaçao fica muito pequena , nao tendo muita mudança
                self.pv = self.pv * 0.9954 + res * 0.002763
                time.sleep(1)
                i += 1


def run():
    fuzzy = Fuzzy()
    client = fuzzy.connect_mqtt()
    client.loop_start()
    fuzzy.publish(client)


run()
