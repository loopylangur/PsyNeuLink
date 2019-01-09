import timeit
import numpy as np
from psyneulink import *

from gym_forager.envs.forager_env import ForagerEnv

num_trials = 5
env = ForagerEnv()
reward = 0
done = False

# These should probably be replaced by reference to ForagerEnv constants:
obs_len = 3
obs_coords = 2
action_len = 2
player_idx = 0
player_obs_start_idx = player_idx * obs_len
player_value_idx = player_idx * obs_len + obs_coords
player_coord_slice = slice(player_obs_start_idx,player_value_idx)
predator_idx = 1
predator_obs_start_idx = predator_idx * obs_len
predator_value_idx = predator_idx * obs_len + obs_coords
predator_coord_slice = slice(predator_obs_start_idx,predator_value_idx)
prey_idx = 2
prey_obs_start_idx = prey_idx * obs_len
prey_value_idx = prey_idx * obs_len + obs_coords
prey_coord_slice = slice(prey_obs_start_idx,prey_value_idx)

player_len = prey_len = predator_len = obs_coords

player_obs = ProcessingMechanism(size=prey_len, function=GaussianDistort, name="PLAYER OBS")
prey_obs = ProcessingMechanism(size=prey_len, function=GaussianDistort, name="PREY OBS")
predator_obs = TransferMechanism(size=predator_len, function=GaussianDistort, name="PREDATOR OBS")

# For future use:
values = TransferMechanism(size=3, name="AGENT VALUES")
reward = TransferMechanism(name="REWARD")

dist = Distance(metric=EUCLIDEAN)

PREDATOR = 0
PREY = 1
ATTEND = 0
DISATTEND = 500
UNDECIDED = 0

def choose_closer_agent_function(variable):
    if variable is None:
        return [0,0]
    player_coord = variable[0]
    predator_coord = variable[1]
    prey_coord = variable[2]
    dist_to_predator = dist([player_coord, predator_coord])
    dist_to_prey = dist([player_coord, prey_coord])
    denom = dist_to_predator + dist_to_prey
    if denom != 0:
        normalized_dist_to_predator = dist_to_predator/denom
        normalized_dist_to_prey = dist_to_prey/denom
        if normalized_dist_to_predator < normalized_dist_to_prey:
            return [PREDATOR]
        else:
            return [PREY]
    return [-1]

def control_allocation_function(variable):

    # FIX: HACK DO DEAL WITH BUG IN WHICH PROJECTION TO Panicky_Control_Mech CAN'T BE SUPPRESSED BY ASSIGNING AS INTERNAL:
    closest_agent = variable[0]-1

    if closest_agent == PREDATOR:
        return [[ATTEND],[DISATTEND]]
    elif closest_agent == PREY:
        return [[DISATTEND],[ATTEND]]
    else:
        return [[UNDECIDED],[UNDECIDED]]

# Use ComparatorMechanism to compute direction of action as difference of coordinates between player and prey:
# note: unitization is done in main loop, to allow compilation of LinearCombination function) (TBI)
greedy_action_mech = ComparatorMechanism(name='ACTION',sample=player_obs,target=prey_obs)

Panicky_control_mech = ControlMechanism(objective_mechanism=ObjectiveMechanism(function=choose_closer_agent_function,
                                                                               monitored_output_states=[player_obs,
                                                                                                        predator_obs,
                                                                                                        prey_obs]),
                                        function = control_allocation_function,
                                        control_signals=[(VARIANCE,predator_obs), (VARIANCE,prey_obs)]
)

agent_comp = Composition(name='PANICKY CONTROL COMPOSITION')
agent_comp.add_c_node(player_obs, required_roles=CNodeRole.ORIGIN)
agent_comp.add_c_node(prey_obs, required_roles=CNodeRole.ORIGIN)
agent_comp.add_c_node(predator_obs, required_roles=CNodeRole.ORIGIN)
agent_comp.add_c_node(greedy_action_mech, required_roles=CNodeRole.TERMINAL)

# FIX: THIS DOESN'T SUCCEED IN REMOVING THE ORIGIN ROLE:
agent_comp.add_c_node(Panicky_control_mech, required_roles=CNodeRole.INTERNAL)

# FIX: THIS DOESN'T SUCCEED IN REMOVING THE ROLES:
agent_comp._analyze_graph()
agent_comp._remove_c_node_role(Panicky_control_mech, CNodeRole.ORIGIN)
agent_comp._remove_c_node_role(Panicky_control_mech.objective_mechanism, CNodeRole.TERMINAL)
agent_comp._analyze_graph()

# agent_comp.show_graph()

def main():

    steps = 0
    start_time = timeit.default_timer()
    for _ in range(num_trials):
        observation = env.reset()
        while True:
            run_results = agent_comp.run(inputs={
                player_obs:[observation[player_coord_slice]],
                predator_obs:[observation[predator_coord_slice]],
                prey_obs:[observation[prey_coord_slice]],
                # values:[observation[player_value_idx],observation[prey_value_idx],observation[predator_value_idx]],
                # reward:[reward],
            })
            action= np.where(run_results[0]==0,0,run_results[0]/np.abs(run_results[0]))
            observation, reward, done, _ = env.step(action)
            steps +=1
            if done:
                break
    stop_time = timeit.default_timer()
    print(f'{steps / (stop_time - start_time):.1f} steps/second, {steps} total steps in '
          f'{stop_time - start_time:.2f} seconds')

if __name__ == "__main__":
    main()
