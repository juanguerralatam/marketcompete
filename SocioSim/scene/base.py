from typing import List

from ..config import Configurable
from ..message import Message, MessagePool
from ..agent import Player
from ..utils import PromptTemplate, get_data_from_database, \
                    send_data_to_database, NAME2PORT

import pandas as pd
import json


class Scene(Configurable):
    def __init__(self, players: List[Player], id: int, type_name: str, log_path: str, **kwargs):
        """
        Initialize a scene
        
        Parameters:
            message_pool (MessagePool): The message pool for the scene
            players (List[Player]): The players in the scene
        """
        super().__init__(players=players, id=id, type_name=type_name, **kwargs)
        # All scenes share a common message pool, prompt assembler and output parser
        self.id = id
        self.players = players
        
        log_path = f'{log_path}/{self.type_name}_{self.id}.txt'
        self.message_pool = MessagePool(log_path=log_path)
        
        self.num_of_players = len(players)
        self.invalid_step_retry = 3
        
        self._curr_turn = 0  # for message turn
        self._curr_player_idx = 0
        self._curr_process_idx = 0
    
    # TODO: 根据需求组装更复杂的prompt
    def add_new_prompt(self, player_name, scene_name=None, step_name=None, data=None, from_db=False):
        # If the prompt template exists, render it and add it to the message pool
        if scene_name and step_name:
            if PromptTemplate([scene_name, step_name]).content:
                prompt_template = PromptTemplate([scene_name, step_name])
                if from_db:
                    data = get_data_from_database(step_name, NAME2PORT[player_name])
                prompt = prompt_template.render(data=data)
        elif isinstance(data, str) and data != "None":
            prompt = data
        else:
            raise ValueError("Prompt not found")
            
        # convert str:prompt to Message:prompt
        message = Message(agent_name='System', content=prompt, 
                            visible_to=player_name, turn=self._curr_turn)
        self.message_pool.append_message(message)
    
    def parse_output(self, output, player_name, step_name, to_db=False):  
        res = output
        
        if to_db and output != "None":  # TODO: better code
            send_data_to_database(output, step_name, NAME2PORT[player_name])
            res = json.loads(output)
        
        # TODO: short output
        message = Message(agent_name=player_name, content=output, 
                            visible_to=player_name, turn=self._curr_turn)
        self.message_pool.append_message(message)
        
        return res
    
    def log_table(self, data, column_name):
        # Try to read the CSV file if it exists, else create an empty DataFrame
        csv_file = f'{self.log_file}.csv'  # TODO: log_file
        try:
            df = pd.read_csv(csv_file)
        except FileNotFoundError:
            df = pd.DataFrame()

        # Check if the 'name' column exists in the DataFrame
        if 'name' not in df.columns:
            df['name'] = data.keys()
            df[column_name] = data.values()
        else:
            # Ensure the order of 'name' in the DataFrame and the data are the same
            # This assumes that the 'name' values in data are already present in the DataFrame
            ordered_values = [data[name] for name in df['name']]
            df[column_name] = ordered_values

        # Print the table and save it to CSV
        print(df)
        df.to_csv(csv_file, index=False)
    
    def is_terminal(self):
        pass
    
    def get_curr_player(self):
        return self.players[self._curr_player_idx]
    
    def get_curr_process(self):
        return self.processes[self._curr_process_idx]
        
    def step(self, data=None):
        pass

    def run(self, previous_scene_data=None):
        """
        Main function, automatically assemble input and parse output to run the scene
        """
        
        # data can from previous scene or previous process
        data = previous_scene_data
        while not self.is_terminal():
            data = self.step(data)
        
        self.terminal_action()