"""
Defines the DataRange1D class.
"""


# Major library imports
from math import ceil, floor, log
from numpy import compress, inf, isnan

# Enthought library imports
from enthought.traits.api import CFloat, Enum, false, Property, Trait, true

# Local relative imports
from base import arg_find_runs, bin_search
from base_data_range import BaseDataRange
from ticks import heckbert_interval


class DataRange1D(BaseDataRange):
    """ Represents a 1-D data range.
    """
    
    # The actual value of the lower bound of this range (overrides 
    # AbstractDataRange). To set it, use **low_setting**.
    low = Property
    # The actual value of the upper bound of this range (overrides
    # AbstractDataRange). To set it, use **high_setting**.
    high = Property
    
    # Property for the lower bound of this range (overrides AbstractDataRange).
    # 
    # * 'auto': The lower bound is automatically set at or below the minimum
    #   of the data.
    # * 'track': The lower bound tracks the upper bound by **tracking_amount**.
    # * CFloat: An explicit value for the lower bound
    low_setting = Property(Trait('auto', 'auto', 'track', CFloat))
    # Property for the upper bound of this range (overrides AbstractDataRange).
    # 
    # * 'auto': The upper bound is automatically set at or above the maximum
    #   of the data.
    # * 'track': The upper bound tracks the lower bound by **tracking_amount**.
    # * CFloat: An explicit value for the upper bound
    high_setting = Property(Trait('auto', 'auto', 'track', CFloat))

    # Do "auto" bounds imply an exact fit to the data? If False, 
    # they pad a little bit of margin on either side.
    tight_bounds = true

    # The minimum percentage difference between low and high.  That is,
    # (high-low) >= epsilon * low.
    epsilon = CFloat(1.0e-20)
    
    # When either **high** or **low** tracks the other, track by this amount.
    default_tracking_amount = CFloat(20.0)
    
    # The current tracking amount. This value changes with zooming.
    tracking_amount = default_tracking_amount
    
    # Default tracking state. This value is used when self.reset() is called.
    #
    # * 'auto': Both bounds reset to 'auto'.
    # * 'high_track': The high bound resets to 'track', and the low bound
    #   resets to 'auto'.
    # * 'low_track': The low bound resets to 'track', and the high bound
    #   resets to 'auto'.
    default_state = Enum('auto','high_track', 'low_track')
    
    # Is this range dependent upon another range?
    fit_to_subset = false

    #------------------------------------------------------------------------
    # Private traits
    #------------------------------------------------------------------------
    
    # The "_setting" attributes correspond to what the user has "set"; the
    # "_value" attributes are the actual numerical values for the given
    # setting.
    
    # The user-specified low setting.
    _low_setting = Trait('auto', 'auto', 'track', CFloat)
    # The actual numerical value for the low setting.
    _low_value = CFloat(-inf)
    # The user-specified high setting.
    _high_setting = Trait('auto', 'auto', 'track', CFloat)
    # The actual numerical value for the high setting.
    _high_value = CFloat(inf)

    # A list of attributes to persist
    # _pickle_attribs = ("_low_setting", "_high_setting")


    #------------------------------------------------------------------------
    # AbstractRange interface
    #------------------------------------------------------------------------
    
    def clip_data(self, data):
        """ Returns a list of data values that are within the range.
        
        Implements AbstractDataRange.
        """
        return compress(self.mask_data(data), data)
    
    def mask_data(self, data):
        """ Returns a mask array, indicating whether values in the given array
        are inside the range.
        
        Implements AbstractDataRange.
        """
        return (data>=self._low_value) & (data<=self._high_value)
    
    def bound_data(self, data):
        """ Returns a tuple of indices for the start and end of the first run
        of *data* that falls within the range.
        
        Implements AbstractDataRange.
        """
        mask = self.mask_data(data)
        runs = arg_find_runs(mask, "flat")
        # Since runs of "0" are also considered runs, we have to cycle through
        # until we find the first run of "1"s.
        for run in runs:
            if mask[run[0]] == 1:
                return run[0],run[1]-1  # arg_find_runs returns 1 past the end
        return (0,0)

    def set_bounds(self, low, high):
        """ Sets all the bounds of the range simultaneously.
        
        Implements AbstractDataRange.
        """
        if low == 'track':
            # Set the high setting first
            self._do_set_high_setting(high, fire_event=False)
            self._do_set_low_setting(low)
        else:
            # Either set low first or order doesn't matter
            self._do_set_low_setting(low, fire_event=False)
            self._do_set_high_setting(high)
            
    def scale_tracking_amount(self, multiplier):
        """ Sets the **tracking_amount** to a new value, scaled by *multiplier*.
        """
        self.tracking_amount = self.tracking_amount * multiplier
        
    def set_tracking_amount(self, amount):
        """ Sets the **tracking_amount** to a new value, *amount*.
        """
        self.tracking_amount = amount
        
    def set_default_tracking_amount(self, amount):
        """ Sets the **default_tracking_amount** to a new value, *amount*.
        """
        self.default_tracking_amount = amount
 
    #------------------------------------------------------------------------
    # Public methods
    #------------------------------------------------------------------------

    def reset(self):
        """ Resets the bounds of this range, based on **default_state**.
        """
        #need to maintain 'track' setting
        if self.default_state == 'auto':
            self._high_setting = 'auto'
            self._low_setting = 'auto'
        elif self.default_state == 'low_track':
            self._high_setting = 'auto'
            self._low_setting = 'track'
        elif self.default_state == 'high_track':
            self._high_setting = 'track'
            self._low_setting = 'auto'
        self._refresh_bounds()
        self.tracking_amount = self.default_tracking_amount
        
    def refresh(self):
        """ If any of the bounds is 'auto', this method refreshes the actual
        low and high values from the set of the view filters' data sources.
        """
        if ('auto' in (self._low_setting, self._high_setting)) or \
            ('track' in (self._low_setting, self._high_setting)):
            # If the user has hard-coded bounds, then refresh() doesn't do
            # anything.
            self._refresh_bounds()
        else:
            return
 
    #------------------------------------------------------------------------
    # Private methods (getters and setters)
    #------------------------------------------------------------------------

    def _get_low(self):
        return float(self._low_value)
    
    def _set_low(self, val):
        return self._set_low_setting(val)
    
    def _get_low_setting(self):
        return self._low_setting

    def _do_set_low_setting(self, val, fire_event=True):
        if self._low_setting != val:
            self._low_setting = val
            if val == 'auto':
                if len(self.sources) > 0:
                    val = min([source.get_bounds()[0] for source in self.sources])
                else:
                    val = -inf
            if val == 'track':
                if len(self.sources) > 0:
                    val = self._high_value - self.tracking_amount
                else:
                    val = -inf
            if self._low_value != val:
                self._low_value = val
                if fire_event:
                    self.updated = (self._low_value, self._high_value)

    def _set_low_setting(self, val):
        self._do_set_low_setting(val, True)

    def _get_high(self):
        return float(self._high_value)
    
    def _set_high(self, val):
        return self._set_high_setting(val)
    
    def _get_high_setting(self):
        return self._high_setting
    
    def _do_set_high_setting(self, val, fire_event=True):
        if self._high_setting != val:
            self._high_setting = val
            if val == 'auto':
                if len(self.sources) > 0:
                    val = max([source.get_bounds()[1] for source in self.sources])
                else:
                    val = inf
            if val == 'track':
                if len(self.sources) > 0:
                    val = self._low_value + self.tracking_amount
                else:
                    val = inf
            if self._high_value != val:
                self._high_value = val
                self.updated = (self._low_value, self._high_value)

    def _set_high_setting(self, val):
        self._do_set_high_setting(val, True)

    def _refresh_bounds(self):
        null_bounds = False
        if len(self.sources) == 0:
            null_bounds = True
        else:
            bounds_list = [source.get_bounds() for source in self.sources \
                              if source.get_size() > 0]

            if len(bounds_list) == 0:
                null_bounds = True
            
        if null_bounds:
            # If we have no sources and our settings are "auto", then reset our
            # bounds to infinity; otherwise, set the _value to the corresponding
            # setting.
            if (self._low_setting in ("auto", "track")):
                self._low_value = -inf
            else:
                self._low_value = self._low_setting
            if (self._high_setting in ("auto", "track")):
                self._high_value = inf
            else:
                self._high_value = self._high_setting
            return
        else:
            mins, maxes = zip(*bounds_list)

            low_start, high_start = calc_bounds(self._low_setting, self._high_setting,
                                                mins, maxes, self.epsilon, 
                                                self.tight_bounds, self.tracking_amount)
                
        
        if (self._low_value != low_start) or (self._high_value != high_start):
            self._low_value = low_start
            self._high_value = high_start
            self.updated = (self._low_value, self._high_value)
        return

    #------------------------------------------------------------------------
    # Event handlers
    #------------------------------------------------------------------------
    
    def _sources_items_changed(self, event):
        self.refresh()
        for source in event.removed:
            source.on_trait_change(self.refresh, "data_changed", remove=True)
        for source in event.added:
            source.on_trait_change(self.refresh, "data_changed")
    
    def _sources_changed(self, old, new):
        self.refresh()
        for source in old:
            source.on_trait_change(self.refresh, "data_changed", remove=True)
        for source in new:
            source.on_trait_change(self.refresh, "data_changed")


    #------------------------------------------------------------------------
    # Serialization interface
    #------------------------------------------------------------------------
    
    def _post_load(self):
        self._sources_changed(None, self.sources)

    

###### method to calculate bounds for a given 1-dimensional set of data
def calc_bounds(low_set, high_set, mins, maxes, epsilon, tight_bounds, track_amount):
    """ Calculates bounds for a given 1-D set of data.
    
    Parameters
    ----------
    low_set : 'auto', 'track', or number
        Current low setting
    high_set : 'auto', 'track', or number
        Current high setting
    mins : list of numbers
        Potential minima.
    maxes : list
        Potential maxima.
    epsilon : number
        Minimum percentage difference between bounds
    tight_bounds : Boolean
        Do 'auto' bounds imply an exact fit to the data? If False, they pad a
        little bit of margin on either side.
    track_amount : number
        The amount by which a 'track' bound tracks another bound.
    
    Returns
    -------
    (min, max) for the new bounds. If either of the calculated bounds is NaN,
    returns (0,0).
    
    Description
    -----------
    Setting both *low_set* and *high_set* to 'track' is an invalid state; 
    the method copes by setting *high_set* to 'auto', and proceeding.
    """
    
    if (low_set == 'track') and (high_set == 'track'):
        high_set = 'auto'
    
    if low_set == 'auto':
        real_min = min(mins)
    elif low_set == 'track':
        #real_max hasn't been set yet
        pass
    else:
        real_min = low_set
            
    if high_set == 'auto':
        real_max = max(maxes)
    elif high_set == 'track':
        #real_min has been set now
        real_max = real_min + track_amount
    else:
        real_max = high_set
    
    #Go back and set real_min if we need to
    if low_set == 'track':
        real_min = real_max - track_amount
        
    
    # If we're all NaNs, just return a 0,1 range
    if isnan(real_max) or isnan(real_min):
        return 0,0

    if abs(real_max - real_min) <= abs(epsilon * real_min):
        # If we get here, then real_min and real_max are (for all
        # intents and purposes) identical, and so we just base
        # everything off of real_min.
        # Note: we have to use <= and not strict < because otherwise
        # we won't catch the cases when real_min == 0.0.
        if abs(real_min) > 1.0:
            # Round up to the next power of ten that encloses these
            log_val = log(abs(real_min), 10)
            if real_min >= 0:
                real_min = pow(10, floor(log_val))
                real_max = pow(10, ceil(log_val))
            else:
                real_min = -pow(10, ceil(log_val))
                real_max = -pow(10, floor(log_val))
        else:
            # If the user has a constant value less than 1, then these
            # are the bounds we use.
            real_min = -1.0
            real_max = 1.0

    if not tight_bounds:
        return heckbert_interval(real_min, real_max)[0:2]
    
    return real_min, real_max
