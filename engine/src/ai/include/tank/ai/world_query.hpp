#pragma once

// Read-only view of world state the ai module is allowed to see, implemented by the sim/app
// layer and handed down to BehaviorSystem::Update(). Together with gameplay_components.hpp,
// this interface is the *entire* surface the ai module depends on outside of entt itself - it
// never touches a concrete Tank/Vehicle type (there isn't one) and never links SDL3.
//
// Left intentionally minimal for M0/M1 - concrete obstacle/mine/projectile queries are added
// as the M2 behavior FSM and targeting/prediction math actually need them, rather than
// speculatively designed now.

namespace tank::ai {

class WorldQuery {
public:
    virtual ~WorldQuery() = default;
};

}  // namespace tank::ai
