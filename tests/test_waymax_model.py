import gpudrive
import pytest
import torch

@pytest.fixture(scope="module")
def sim_init():
    reward_params = gpudrive.RewardParams()
    reward_params.rewardType = gpudrive.RewardType.DistanceBased 
    reward_params.distanceToGoalThreshold = 1.0 
    reward_params.distanceToExpertThreshold = 1.0  

    params = gpudrive.Parameters()
    params.polylineReductionThreshold = 0.5  
    params.observationRadius = 10.0 
    params.collisionBehaviour = gpudrive.CollisionBehaviour.AgentStop  
    params.datasetInitOptions = gpudrive.DatasetInitOptions.PadN  
    params.rewardParams = reward_params 
    params.maxNumControlledVehicles = 2 # we are going to use the second vehicle as the controlled vehicle
    params.IgnoreNonVehicles = True
    params.useWayMaxModel = True

    sim = gpudrive.SimManager(
        exec_mode=gpudrive.madrona.ExecMode.CPU,
        gpu_id=0,
        num_worlds=1,
        auto_reset=False,
        json_path="tests/pytest_data",
        params=params
    )

    return sim

def test_forward_inverse_dynamics(sim_init):
    sim = sim_init
    
    valid_agent_idx = 1
    done_tensor = sim.done_tensor().to_torch()
    expert_trajectory_tensor = sim.expert_trajectory_tensor().to_torch()
    action_tensor = sim.action_tensor().to_torch()
    absolute_obs = sim.absolute_self_observation_tensor().to_torch()
    self_obs = sim.self_observation_tensor().to_torch()
    actions = torch.zeros_like(action_tensor)

    traj = expert_trajectory_tensor[:,valid_agent_idx].squeeze()
    pos = traj[:2*91].view(91,2)
    vel = traj[2*91:4*91].view(91,2)
    headings = traj[4*91:5*91].view(91,1)
    invActions = traj[6*91:].view(91,3)
    i = 0

    position = absolute_obs[0,valid_agent_idx,:2]
    heading = absolute_obs[0,valid_agent_idx,7]
    speed = self_obs[0, valid_agent_idx, 0]

    assert torch.allclose(position, pos[i], atol=1e-2), f"Position mismatch: {position} vs {pos[i]}"
    assert pytest.approx(heading.item(), abs=1e-2) == headings[i].item(), f"Heading mismatch: {heading.item()} vs {headings[i].item()}"
    assert pytest.approx(speed.item(), abs=1e-2) == torch.norm(vel[i]).item(), f"Speed mismatch: {speed.item()} vs {torch.norm(vel[i]).item()}"

    while not done_tensor[:,valid_agent_idx].all():
        actions[:,valid_agent_idx,:] = invActions[i]
        action_tensor.copy_(actions)
        sim.step()
        i+=1
        
        assert torch.allclose(position, pos[i], atol=1e-2), f"Position mismatch: {position} vs {pos[i]}"
        assert pytest.approx(heading.item(), abs=1e-2) == headings[i].item(), f"Heading mismatch: {heading.item()} vs {headings[i].item()}"
        assert pytest.approx(speed.item(), abs=1e-2) == torch.norm(vel[i]).item(), f"Speed mismatch: {speed.item()} vs {torch.norm(vel[i]).item()}"