#!/bin/perl
#
# Author: Denis B.
# Description: A script for adding matching layers of one object to another.
#              Used to construct gcode for multiple extruder printers.
#              Requires penultimate gcode from skeinforge.
#


# =======================> print usage and die
sub dieHelpUsage {
   print STDERR "Usage: $0 <base_obj.g> <color_obj.g> [color_on.g] [color_off.g]\n";
   print STDERR "The input gcode should be the \"penultimate\" one (see export plugin)\n";
   print STDERR "The script will add the matching layers from the second file into the\n";
   print STDERR "first one prefixing and suffixing the additions from the harcoded \n";
   print STDERR "\"color_on.g\" and \"color_off.g\" files. The comments are stripped.\n";
   die;
}


# =======================> start

# names and path for the alternate start/end gcode files
my $alt_path = "c:/Printrun/.skeinforge/alterations";

my $argc = $#ARGV;
if($argc < 1) {
  dieHelpUsage();
}

my $fn_base = shift(@ARGV);
my $fn_color = shift(@ARGV);
my $fn_alt_start = shift(@ARGV);
my $fn_alt_end = shift(@ARGV);

if(length($fn_alt_start) == 0) {
  $fn_alt_start = "$alt_path/pla_c_on.gcode";
}
if(length($fn_alt_end) == 0) {
  $fn_alt_end = "$alt_path/pla_c_off.gcode";
}

open(ALTSTART, "<$fn_alt_start") or die "Can't open $fn_alt_start for read: ",$!,"\n";
open(ALTEND, "<$fn_alt_end") or die "Can't open $fn_alt_end for read: ",$!,"\n";

open(BASE, "<$fn_base") or die "Can't open $fn_base for read: ",$!,"\n";
open(COLOR, "<$fn_color") or die "Can't open $fn_color for read: ",$!,"\n";

# Read in the alt start and stop files
my $alt_start = "";
while(<ALTSTART>) {
  chomp;
  s/\s*;.*//;
  s/\s*\(.*//;
  s/\s*$//;
  if(length($_) > 0) {
    $alt_start .= "$_\n"; 
  }
}
close ALTSTART;
my $alt_stop = "";
while(<ALTEND>) {
  chomp;
  s/\s*;.*//;
  s/\s*\(.*//;
  s/\s*$//;
  if(length($_) > 0) {
    $alt_stop .= "$_\n";
  }
}
close ALTEND;

# Read in the layers of the color model, format: (<layer> 0.32 )
my %color_layer;
my $layer_height = 0.00;
my $g_one_seen = 0;
my $layer_code;
while(<COLOR>) {
  if( !(/<layer>/ .. /<\/layer>/) ) { next; }
  if(/<\/layer>/) { 
    # If there was any movement keep the layer
    if($g_one_seen > 0) {
      $color_layer{$layer_height} = $layer_code;
    }
    $layer_code = ""; 
    $g_one_seen = 0; 
    next; 
  }
  if(/<layer>\s+([\d\.]+)/) {  $layer_height = $1; }
  chomp;
  s/\s*;.*//;
  s/\s*\(.*//;
  s/\s*$//;
  if(length($_) > 0) {
    $layer_code .= "$_\n";
    if(/^[gG]1\s/) {
      $g_one_seen = 1;
    }
  }
}
close COLOR;

# Read and print the base gcode lines doing what the script is designed for
$layer_height = 0.00;
while(<BASE>) {
  # capture the layer height
  if(/<layer>\s+([\d\.]+)/) { $layer_height = $1; next; }
  # if done with the layer add matching color part layer
  if(/<\/layer>/ && length($color_layer{$layer_height}) != 0) { 
    print $alt_start, $color_layer{$layer_height}, $alt_stop;
    next;
  }
  chomp;
  s/\s*;.*//;
  s/\s*\(.*//;
  s/\s*$//;
  if(length($_) > 0) {
    print "$_\n";
  }
}
close BASE;

