use Test::More tests => 7;
use strict;
use warnings;

BEGIN {
    use FindBin;
    use lib "$FindBin::Bin/../lib";
}

use List::Util qw(first sum);
use Slic3r;
use Slic3r::Geometry qw(scale PI);
use Slic3r::Test;

{
    my $config = Slic3r::Config->new_from_defaults;
    $config->set('skirts', 1);
    $config->set('brim_width', 2);
    $config->set('perimeters', 3);
    $config->set('fill_density', 0.4);
    $config->set('bottom_solid_layers', 1);
    $config->set('first_layer_extrusion_width', 2);
    $config->set('first_layer_height', '100%');
    
    my $print = Slic3r::Test::init_print('20mm_cube', config => $config);
    my @E_per_mm = ();
    Slic3r::GCode::Reader->new->parse(my $gcode = Slic3r::Test::gcode($print), sub {
        my ($self, $cmd, $args, $info) = @_;
        
        if ($self->Z == $config->layer_height) {  # only consider first layer
            if ($info->{extruding} && $info->{dist_XY} > 0) {
                push @E_per_mm, $info->{dist_E} / $info->{dist_XY};
            }
        }
    });
    my $E_per_mm_avg = sum(@E_per_mm) / @E_per_mm;
    ok !(defined first { abs($_ - $E_per_mm_avg) > 0.01 } @E_per_mm),
        'first_layer_extrusion_width applies to everything on first layer';
}

{
    my $config = Slic3r::Config->new_from_defaults;
    $config->set('bridge_speed', 99);
    $config->set('bridge_flow_ratio', 1);
    $config->set('cooling', 0);                 # to prevent speeds from being altered
    $config->set('first_layer_speed', '100%');  # to prevent speeds from being altered
    
    my $test = sub {
        my $print = Slic3r::Test::init_print('overhang', config => $config);
        my @E_per_mm = ();
        Slic3r::GCode::Reader->new->parse(my $gcode = Slic3r::Test::gcode($print), sub {
            my ($self, $cmd, $args, $info) = @_;
        
            if ($info->{extruding} && $info->{dist_XY} > 0) {
                if (($args->{F} // $self->F) == $config->bridge_speed*60) {
                    push @E_per_mm, $info->{dist_E} / $info->{dist_XY};
                }
            }
        });
        my $expected_mm3_per_mm = ($config->nozzle_diameter->[0]**2) * PI/4 * $config->bridge_flow_ratio;
        my $expected_E_per_mm = $expected_mm3_per_mm / ((($config->filament_diameter->[0]/2)**2)*PI);
        ok !(defined first { abs($_ - $expected_E_per_mm) > 0.01 } @E_per_mm),
            'expected flow when using bridge_flow_ratio = ' . $config->bridge_flow_ratio;
    };
    
    $config->set('bridge_flow_ratio', 0.5);
    $test->();
    $config->set('bridge_flow_ratio', 2);
    $test->();
    $config->set('extrusion_width', 0.4);
    $config->set('bridge_flow_ratio', 1);
    $test->();
    $config->set('bridge_flow_ratio', 0.5);
    $test->();
    $config->set('bridge_flow_ratio', 2);
    $test->();
}

{
    my $config = Slic3r::Config->new_from_defaults;
    $config->set('bridge_speed', 99);
    $config->set('bridge_flow_ratio', 1);
    $config->set('bridge_spacing_multiplier', 2.0);
    $config->set('cooling', 0);                 # to prevent speeds from being altered
    $config->set('first_layer_speed', '100%');  # to prevent speeds from being altered
    $config->set('bridge_flow_ratio', 0.5);

    my $test = sub {
        my $dist_E = 0.0;
        my $print = Slic3r::Test::init_print('overhang', config => $config);
        Slic3r::GCode::Reader->new->parse(my $gcode = Slic3r::Test::gcode($print), sub {
            my ($self, $cmd, $args, $info) = @_;
            if ($info->{extruding}) {
                $dist_E += $info->{dist_E};
            }
        });
        return $dist_E;
    };
    
    $config->set('bridge_spacing_multiplier', 1.1);
    my $dist_E = $test->();
    $config->set('bridge_spacing_multiplier', 2.0);
    my $dist_E_2 = $test->();
    $config->set('bridge_spacing_multiplier', 0.5);
    my $dist_E_p5 = $test->();
    ok !($dist_E_2 >= $dist_E || $dist_E >= $dist_E_p5),
            "expected higher bridge_spacing_multiplier causing lower extrusion amount, multiplier values (1.1, 2, 0.5), E-distances ($dist_E, $dist_E_2, $dist_E_p5)";
}

__END__
