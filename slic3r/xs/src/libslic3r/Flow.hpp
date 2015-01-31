#ifndef slic3r_Flow_hpp_
#define slic3r_Flow_hpp_

#include <myinit.h>
#include "Config.hpp"
#include "ExtrusionEntity.hpp"

namespace Slic3r {

#define BRIDGE_EXTRA_SPACING 0.05
#define OVERLAP_FACTOR 1.0

enum FlowRole {
    frExternalPerimeter,
    frPerimeter,
    frInfill,
    frSolidInfill,
    frTopSolidInfill,
    frSupportMaterial,
    frSupportMaterialInterface,
};

class Flow
{
    public:
    float width, height, nozzle_diameter, bridge_spacing_multiplier;
    bool bridge;
    
    Flow(float _w, float _h, float _nd, bool _bridge = false, float _bridge_spacing_multiplier = 0.0)
        : width(_w), height(_h), nozzle_diameter(_nd), bridge(_bridge), bridge_spacing_multiplier(_bridge_spacing_multiplier) {};
    float spacing() const;
    float spacing(const Flow &other) const;
    double mm3_per_mm() const;
    coord_t scaled_width() const {
        return scale_(this->width);
    };
    coord_t scaled_spacing() const {
        return scale_(this->spacing());
    };
    
    static Flow new_from_config_width(FlowRole role, const ConfigOptionFloatOrPercent &width, float nozzle_diameter, float height, float bridge_flow_ratio, float bridge_spacing_multiplier);
    static Flow new_from_spacing(float spacing, float nozzle_diameter, float height, float bridge_spacing_multiplier);
    
    private:
    static float _bridge_width(float nozzle_diameter, float bridge_flow_ratio);
    static float _auto_width(FlowRole role, float nozzle_diameter, float height);
    static float _width_from_spacing(float spacing, float nozzle_diameter, float height, float bridge_spacing_multiplier);
    /*static float _spacing(float width, float nozzle_diameter, float height, float bridge_flow_ratio);*/
};

}

#endif
