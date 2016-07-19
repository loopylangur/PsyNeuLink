# Princeton University licenses this file to You under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.  You may obtain a copy of the License at:
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
# on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and limitations under the License.
#
#
# *************************************************  EVCMechanism ******************************************************
#

from collections import OrderedDict
from inspect import isclass
from Functions.Mechanisms.SystemControlMechanism import *
from Functions.Mechanisms.Mechanism import MonitoredOutputStatesOption
from Functions.Mechanisms.AdaptiveIntegrator import AdaptiveIntegratorMechanism

from Functions.ShellClasses import *
from Functions.Mechanisms.SystemControlMechanism import SystemControlMechanism_Base

# from multiprocessing import Pool

from mpi4py import MPI


ControlSignalChannel = namedtuple('ControlSignalChannel',
                                  'inputState, variableIndex, variableValue, outputState, outputIndex, outputValue')

OBJECT = 0
EXPONENT = 1
WEIGHT = 2

PARALLELIZE = False

class EVCError(Exception):
    def __init__(self, error_value):
        self.error_value = error_value

    def __str__(self):
        return repr(self.error_value)


class EVCMechanism(SystemControlMechanism_Base):
    """Maximize EVC over specified set of control signals for values of monitored states

    Description:
        + Implements EVC maximization (Shenhav et al. 2013)
        [DOCUMENATION HERE:]

        NOTE: self.execute serves as kwValueAggregationFunction
        ALTERNATIVE:  IMPLEMENT FOLLOWING IN paramClassDefaults:
                                       kwValueAggregationFunction:
                                               LinearCombination(
                                                   param_defaults={kwOffset:0,
                                                                   kwScale:1,
                                                                   kwOperation:LinearCombination.Operation.SUM},
                                                   context=functionType+kwValueAggregationFunction),
        # INSTANTIATION:
        # - specification of system:  required param: kwSystem
        # - kwDefaultController:  True =>
        #         takes over all projections from default Controller;
        #         does not take monitored states (those are created de-novo)
        # TBI: - kwControlSignalProjections:
        #         list of projections to add (and for which outputStates should be added)
        # - inputStates: one for each performance/environment variable monitiored


# DOCUMENT:
# 1) Add a predictionMechanism for each origin (input) Mechanism in self.system,
#        and a Process for each pair: [origin, kwIdentityMatrix, prediction]
# 2) Implement self.simulatedSystem that, for each originMechanism
#        replaces Process.inputState with predictionMechanism.value
# 3) Modify EVCMechanism.update() to execute self.simulatedSystem rather than self.system
#    CONFIRM: EVCMechanism.system is never modified in a way that is not reflected in EVCMechanism.simulatedSystem
#                (e.g., when learning is implemented)
# 4) Implement controlSignal allocations for optimal allocation policy in EVCMechanism.system



# NOTE THAT EXCECUTE METHOD ~ ValueAggregationFunction (i.e,. analogous to CostAggregationFunction

# DESCRIBE USE OF MonitoredOutputStatesOptions VS. EXPLICIT SPECIFICADTION OF MECHANISM AND/OR MECHANISMSTATES
# CAN SPECIFIY WEIGHTS IF LIST OF MECHANISMS/ MECHANISMSTATES IS PROVIDED, IN WHICH CASE #WEIGHTS MUST = #STATES SPECIFIED
#              OTHEREWISE (IF MonitoredOutputStatesOptions OR DEFAULT IS USED, WEIGHTS ARE IGNORED

# GET FROM System AND/OR Mechanism
#     kwMonitoredOutputStates must be list of Mechanisms or MechanismOutputStates in Mechanisms that are in kwSystem
#     if Mechanism is specified in kwMonitoredOutputStates, all of its outputStates are used
#     kwMonitoredOutputStates assigns a Mapping Projection from each outputState to a newly created inputState in self.inputStates
#     executeMethod uses LinearCombination to apply a set of weights to the value of each monitored state to compute EVC
#     and then searches space of control signals (using allocationSamples for each) to find combiantion that maxmizes EVC
                this is overridden if None is specified for kwMonitoredOutputStates in the outputState itself

        #    - wherever a ControlSignal projection is specified, using kwEVC instead of kwControlSignal
        #        this should override the default sender kwSystemDefaultController in ControlSignal.instantiate_sender
        #    ? expclitly, in call to "EVC.monitor(input_state, parameter_state=NotImplemented) method
        # - specification of executeMethod: default is default allocation policy (BADGER/GUMBY)
        #     constraint:  if specified, number of items in variable must match number of inputStates in kwInputStates
        #                  and names in list in kwMonitor must match those in kwInputStates

#      OBJECTIVE FUNCTION FOR exeuteMethod:
#      Applies linear combination to values of monitored states (self.inputStates)
#      executeMethod is LinearCombination, with weights = linear terms
#      kwExecuteMethodParams = kwWeights
#      Cost is aggregated over controlSignal costs using kwCostAggregationFunction (default: LinearCombination)
            currently, it is specified as an instantiated function rather than a reference to a class
#      Cost is combined with values (aggregated by executeMethod) using kwCostApplicationFunction
 (          default: LinearCombination)
            currently, it is specified as an instantiated function rather than a reference to a class

        # EVALUATION:
        # - evaluation function (as execute method) with one variable item (1D array) for each inputState
        # - mapping projections from monitored states to inputStates
        # - control signal projections established automatically by system implementation (using kwConrolSignal)
        #
        # EXECUTION:
        # - call system.execute for each point in search space
        # - compute evaluation function, and keep track of performance outcomes

    Class attributes:
        + functionType (str): System Default Mechanism
        + paramClassDefaults (dict):
            + kwSystem (System)
            + kwMonitoredOutputStates (list of Mechanisms and/or MechanismOutputStates)

    Class methods:
        None

    Instance attributes:
        system (System):
            System of which EVCMechanism is component, and that it executes to determine the EVC
        predictionMechanisms (list): list of predictionMechanisms added to System for self.system.originMechanisms
        predictionProcesses (list): list of prediction Processes added to System
        controlSignalSearchSpace (list of np.ndarrays):
            list of all combinations of all allocationSamples for all ControlSignal Projections
            for all outputStates in self.outputStates;
            each item in the list is an np.ndarray, the dimension of which is the number of self.outputStates
        MonitoredOutputStates (list): each item is a MechanismOutputState that sends a projection to a corresponding
            inputState in the ordered dict self.inputStates
        monitoredValues (3D np.nparray): values of monitored states (self.inputStates) from call of self.executeMethod
        EVCmax (2D np.array):
            values of monitored states (self.inputStates) for EVCmax
        EVCmaxPolicy (1D np.array):
            vector of values (ControlSignal allocations) for EVCmax, one for each outputState in self.outputStates

    Instance methods:
        • validate_params(request_set, target_set, context):
            insure that kwSystem is specified, and validate specifications for monitored states
        • validate_monitored_state(item):
            validate that all specifications for a monitored state are either a Mechanism or MechanismOutputState
        • instantiate_attributes_before_execute_method(context):
            assign self.system and monitoring states (inputStates) specified in kwMonitoredOutputStates
        • instantiate_monitored_output_states(monitored_states, context):
            parse list of MechanismOutputState(s) and/or Mechanism(s) and call instantiate_monitoring_input_state for each item
        • instantiate_monitoring_input_state(output_state, context):
            extend self.variable to accomodate new inputState
            create new inputState for outputState to be monitored, and assign Mapping Project from it to inputState
        • instantiate_control_signal_projection(projection, context):
            adds outputState, and assigns as sender of to requesting ControlSignal Projection
        • instantiate_execute_method(context):
            construct self.controlSignalSearchSpace from the allocationSamples for the
            ControlSignal Projection associated with each outputState in self.outputStates
        • update(time_scale, runtime_params, context)
            execute System for each combination of controlSignals in self.controlSignalSearchSpace,
                store output values in self.EVCvalues, identify and store maximum in self.EVCmax,
                store the corresponding combination of ControlSignal allocations self.EVCmaxPolicy,
                and assign those allocations to outputState.values
        • execute(params, time_scale, context):
            execute self.system for a combination of controlSignals from self.controlSignalSearchSpace
        • add_monitored_state(state, context):
             validates state as Mechanism or MechanismOutputState specification;
             adds inputState to self.inputStates with Mapping Projection from state
             Note:  used by other objects to add outputState(s) to be monitored by EVC

    """

    functionType = "EVCMechanism"

    classPreferenceLevel = PreferenceLevel.TYPE
    # Any preferences specified below will override those specified in TypeDefaultPreferences
    # Note: only need to specify setting;  level will be assigned to Type automatically
    # classPreferences = {
    #     kwPreferenceSetName: 'SystemDefaultControlMechanismCustomClassPreferences',
    #     kp<pref>: <setting>...}

    # This must be a list, as there may be more than one (e.g., one per controlSignal)
    variableClassDefault = [defaultControlAllocation]

    from Functions.Utility import LinearCombination
    # from Functions.__init__ import DefaultSystem
    paramClassDefaults = SystemControlMechanism_Base.paramClassDefaults.copy()
    paramClassDefaults.update({kwSystem: None,
                               # Assigns EVC as DefaultController
                               kwMakeDefaultController:True,
                               # Saves all ControlAllocationPolicies and associated EVC values (in addition to max)
                               kwSaveAllPoliciesAndValues: False,
                               # Can be replaced with a list of MechanismOutputStates or Mechanisms
                               #     the values of which are to be monitored
                               kwMonitoredOutputStates: [MonitoredOutputStatesOption.PRIMARY_OUTPUT_STATES],
                               # ExecuteMethod and params specifies value aggregation function
                               kwExecuteMethod: LinearCombination,
                               kwExecuteMethodParams: {kwMechanismParameterStates: None,
                                                       kwOffset: 0,
                                                       kwScale: 1,
                                                       # Must be a vector with length = length of kwMonitoredOutputStates
                                                       # kwWeights: [1],
                                                       kwOperation: LinearCombination.Operation.PRODUCT},
                               # CostAggregationFunction specifies how costs are combined across ControlSignals
                               # kwWeight can be added, in which case it should be equal in length
                               #     to the number of outputStates (= ControlSignal Projections)
                               kwCostAggregationFunction:
                                               LinearCombination(
                                                   param_defaults={kwOffset:0,
                                                                   kwScale:1,
                                                                   kwOperation:LinearCombination.Operation.SUM},
                                                   context=functionType+kwCostAggregationFunction),
                               # CostApplicationFunction specifies how aggregated cost is combined with
                               #     aggegated value computed by ExecuteMethod to determine EVC
                               kwCostApplicationFunction:
                                                LinearCombination(
                                                    param_defaults={kwOffset:0,
                                                                    kwScale:1,
                                                                    kwOperation:LinearCombination.Operation.SUM},
                                                    context=functionType+kwCostApplicationFunction),
                               # Mechanism class used for prediction mechanism(s)
                               # Note: each instance will be named based on origin mechanism + kwPredictionMechanism,
                               #       and assigned an outputState named based on the same
                               kwPredictionMechanismType:AdaptiveIntegratorMechanism,
                               # MODIFIED 7/16/16 NEW:
                               kwPredictionMechanismParams:{kwMonitoredOutputStates:None}
                               # MODIFIED END
                               })

    def __init__(self,
                 default_input_value=NotImplemented,
                 params=NotImplemented,
                 name=NotImplemented,
                 prefs=NotImplemented):
                 # context=NotImplemented):

        # Assign functionType to self.name as default;
        #  will be overridden with instance-indexed name in call to super
        if name is NotImplemented:
            self.name = self.functionType

        self.functionName = self.functionType
        self.controlSignalChannels = OrderedDict()

        super(EVCMechanism, self).__init__(default_input_value=default_input_value,
                                        params=params,
                                        name=name,
                                        prefs=prefs,
                                        context=self)

#     def instantiate_attributes_before_execute_method(self, context=NotImplemented):
# # DOCUMENT: ADD PREDICTION MECHANISMS
# # DOCUMENT:
# #     NEED TO SUPPRESS super CALL TO instantiate_execute_method_parameter_states
# #     PROBLEM:
# #          - want to keep parameters (for customizing EVCMechanism.executeMethod()
# #          - but don't want parameter states for them:
# #               - no need (since they won't be subject to control
# #               - parameterState.executeMethod can't handle kwOperation as its variable!
# #     ?? SOLUTION:
# #          - add kwParameterStates: None as specification in kwExecuteMethodParams that suppresses parameterStates
# #              - add to EVCMechanism paramClassDefaults
# #              - add handling to Mechanism.instantiate_execute_method_parameter_states()
# #              - add DOCUMENTATION in Functions and/or Mechanisms or MechanismParameterStates
#
#         """Instantiate inputState(s) specified in kwMonitoredOutputStates and predictionMechanisms
#
#         If kwMonitoredOutputStates is NOT specified:
#             assign an inputState for each outputState of each Mechanism in system.terminalMechanisms
#         If kwMonitoredOutputStates IS specified:
#             assign an inputState for each MechanismOutState specified
#             assign an inputState for all of the outputStates for each Mechanism specified
#         For each originMechanism in self.system, add a predictionMechanism
#
#         """
#
#         # MODIFIED 7/12/16 NEW:
#         # Note: instantiate_input_states is overridden to call self.instantiate_prediction_mechanisms()
          #       and self.instantiate_monitoring_input_state()


    def instantiate_input_states(self, context=NotImplemented):
        """Instantiate inputState and Mapping Projections for list of Mechanisms and/or MechanismStates to be monitored

        Parse paramsCurent[kwMonitoredOutputStates] for system, controller, mechanisms and/or their outputStates:
            - if it specification in outputState is None:
               do NOT monitor this state (this overrides any other specifications)
            - if an outputState is specified in ANY kwMonitoredOutputStates, monitor it (this overrides any other specs)
            - if a mechanism is terminal and/or specified in the system or controller:
                if MonitoredOutputStatesOptions is PRIMARY_OUTPUT_STATES:  monitor only its primary (first) outputState
                if MonitoredOutputStatesOptions is ALL_OUTPUT_STATES:  monitor all of its outputStates
            Note: precedence is given to MonitoredOutputStatesOptions specification in mechanism > controller > system

        Assign inputState to controller for each state to be monitored;  for each item in self.monitoredOutputStates:
            - if it is a MechanismOutputState, call instantiate_monitoring_input_state()
            - if it is a Mechanism, call instantiate_monitoring_input_state for relevant Mechanism.outputStates
                (determined by whether it is a terminal mechanism and/or MonitoredOutputStatesOption specification)

        Notes:
        * MonitoredOutputStatesOption is an AutoNumbered Enum declared in SystemControlMechanism
            - it specifies options for assigning outputStates of terminal Mechanisms in the System
                to self.monitoredOutputStates;  the options are:
                + PRIMARY_OUTPUT_STATES: assign only the primary outputState for each terminal Mechanism
                + ALL_OUTPUT_STATES: assign all of the outputStates of each terminal Mechanism
            - precedence is given to MonitoredOutputStatesOptions specification in mechanism > controller > system
        * self.monitoredOutputStates is a list, each item of which is a Mechanism.outputState from which a projection
            will be instantiated to a corresponding inputState of the SystemControlMechanism
        * self.inputStates is the usual ordered dict of states,
            each of which receives a projection from a corresponding item in self.monitoredOutputStates

        """

        # DOCUMENT:  NOTE:  THESE WILL NOW BE TERMINAL MECHANISMS, AND THEIR ASSOCIATED INPUT MECHANISMS WILL NOT BE
        #                   IF AN ASSOCIATED INPUT MECHANISM NEEDS TO BE MONITORED (E.G., A REWARD INPUT),
        #                   IT MUST BE SPECIFIED IN kwMonitoredOutputStates EXPLICITLY
        self.instantiate_prediction_mechanisms(context=context)

        from Functions.Mechanisms.Mechanism import MonitoredOutputStatesOption
        from Functions.MechanismStates.MechanismOutputState import MechanismOutputState

        # Clear self.variable, as items will be assigned in call(s) to instantiate_monitoring_input_state()
        self.variable = None

        # PARSE SPECS

        controller_specs = []
        system_specs = []
        mech_specs = []
        all_specs = []

        # Get controller's kwMonitoredOutputStates specifications (optional, so need to try)
        try:
            controller_specs = self.paramsCurrent[kwMonitoredOutputStates]
        except KeyError:
            pass

        # Get system's kwMonitoredOutputStates specifications (specified in paramClassDefaults, so must be there)
        system_specs = self.system.paramsCurrent[kwMonitoredOutputStates]

        # If controller has a MonitoredOutputStatesOption specification, remove any such spec from system specs
        if (any(isinstance(item, MonitoredOutputStatesOption) for item in controller_specs)):
            option_item = next((item for item in system_specs if isinstance(item, MonitoredOutputStatesOption)),None)
            if option_item:
                del system_specs[option_item]

        # Combine controller and system specs
        all_specs = controller_specs + system_specs

        # Extract references to mechanisms and/or outputStates from any tuples
        # Note: leave tuples all_specs for use in genreating exponent and weight arrays below
        all_specs_extracted_from_tuples = []
        for item in all_specs:
            # Extract references from specification tuples
            if isinstance(item, tuple):
                all_specs_extracted_from_tuples.append(item[OBJECT])
                continue
            # Validate remaining items as one of the following:
            elif isinstance(item, (Mechanism, MechanismOutputState, MonitoredOutputStatesOption, str)):
                all_specs_extracted_from_tuples.append(item)
            # IMPLEMENTATION NOTE: This should never occur, as should have been found in validate_monitored_state() 
            else:
                raise EVCError("PROGRAM ERROR:  illegal specification ({0}) encountered by {1} "
                               "in kwMonitoredOutputStates for a mechanism, controller or system in its scope".
                               format(item, self.name))

        # Get MonitoredOutputStatesOptions specification from controller or System:
        # FIX: VALIDATE THAT THERE IS ONLY ONE MonitoredOutputStatesOption SPECIFICTION ALL_SPECS
        ctlr_or_sys_option_spec = next((s for s in all_specs if isinstance(s, MonitoredOutputStatesOption)), None)

        # Get kwMonitoredOutputStates specifications for each mechanism and outputState in the System
        # Assign outputStates to self.monitoredOutputStates
        self.monitoredOutputStates = []
        
        # Notes:
        # * Use all_specs to accumulate specs from all mechanisms and their outputStates
        #     for use in generating exponents and weights below)
        # * Use local_specs to combine *only current* mechanism's specs with those from controller and system specs;
        #     this allows the specs for each mechanism and its outputStates to be evaluated independently of any others
        controller_and_system_specs = all_specs_extracted_from_tuples.copy()

        for mech in self.system.mechanisms:

            # For each mechanism:
            # - add its specifications to all_specs (for use below in generating exponents and weights)
            # - extract references to Mechanisms and outputStates from any tuples, and add specs to local_specs
            # - assign MonitoredOutputStatesOptions (if any) to option_spec, (overrides one from controller or system)
            # - use local_specs (which now has this mechanism's specs with those from controller and system specs)
            #     to assign outputStates to self.monitoredStates

            mech_specs = []
            output_state_specs = []
            local_specs = controller_and_system_specs.copy()
            option_spec = ctlr_or_sys_option_spec

            # PARSE MECHANISM'S SPECS

            # Get kwMonitoredOutputStates specification from mechanism 
            try:
                mech_specs = mech.paramsCurrent[kwMonitoredOutputStates]

                if mech_specs is NotImplemented:
                    raise AttributeError

                # Setting kwMonitoredOutputStates to None specifies mechanism's outputState(s) should NOT be monitored
                if mech_specs is None:
                    raise ValueError

            # Mechanism's kwMonitoredOutputStates is absent or NotImplemented, so proceed to parse outputState(s) specs
            except (KeyError, AttributeError):
                pass

            # Mechanism's kwMonitoredOutputStates is set to None, so do NOT monitor any of its outputStates
            except ValueError:
                continue

            # Parse specs in mechanism's kwMonitoredOutputStates
            else:

                # Add mech_specs to all_specs
                all_specs.extend(mech_specs)

                # Extract refs from tuples and add to local_specs
                for item in mech_specs:
                    if isinstance(item, tuple):
                        local_specs.append(item[OBJECT])
                        continue
                    local_specs.append(item)

                # Set option_spec to mechanism's MonitoredOutputStatesOption specification if present
                try:
                    # FIX: VALIDATE THAT THERE IS ONLY ONE MonitoredOutputStatesOption SPECIFICTION IN MECH_SPECS
                    option_spec = next(s for s in mech_specs if isinstance(s, MonitoredOutputStatesOption))
                except StopIteration:
                    pass

            # PARSE OUTPUT STATE'S SPECS

            # for output_state_name, output_state in list(mech.outputStates.items()):
            for output_state_name, output_state in mech.outputStates.items():

                # Get kwMonitoredOutputStates specification from outputState
                try:
                    output_state_specs = output_state.paramsCurrent[kwMonitoredOutputStates]
                    if output_state_specs is NotImplemented:
                        raise AttributeError

                    # Setting kwMonitoredOutputStates to None specifies outputState should NOT be monitored
                    if output_state_specs is None:
                        raise ValueError

                # outputState's kwMonitoredOutputStates is absent or NotImplemented, so ignore
                except (KeyError, AttributeError):
                    pass

                # outputState's kwMonitoredOutputStates is set to None, so do NOT monitor it
                except ValueError:
                    continue

                # Parse specs in outputState's kwMonitoredOutputStates
                else:

                    # Note: no need to look for MonitoredOutputStatesOption as it has no meaning
                    #       as a specification for an outputState

                    # Add outputState specs to all_specs and local_specs
                    all_specs.extend(output_state_specs)

                    # Extract refs from tuples and add to local_specs
                    for item in output_state_specs:
                        if isinstance(item, tuple):
                            local_specs.append(item[OBJECT])
                            continue
                        local_specs.append(item)

            # Ignore MonitoredOutputStatesOption if any outputStates are explicitly specified for the mechanism
            for output_state_name, output_state in list(mech.outputStates.items()):
                if (output_state in local_specs or output_state.name in local_specs):
                    option_spec = None


            # ASSIGN SPECIFIED OUTPUT STATES FOR MECHANISM TO self.monitoredStates

            for output_state_name, output_state in list(mech.outputStates.items()):

                # If outputState is named or referenced anywhere, include it
                # # MODIFIED 7/16/16 OLD:
                # if (output_state in local_specs or
                #             output_state.name in local_specs or
                #             output_state.name in all_specs_extracted_from_tuples):
                # MODIFIED 7/16/16 NEW:
                if (output_state in local_specs or output_state.name in local_specs):
                # MODIFIED 7/16/16 END
                    self.monitoredOutputStates.append(output_state)
                    continue

                if option_spec is None:
                    continue
                # if option_spec is MonitoredOutputStatesOption.ONLY_SPECIFIED_OUTPUT_STATES:
                #     continue

                # If mechanism is named or referenced in any specification or it is a terminal mechanism
                elif (mech.name in local_specs or mech in local_specs or
                              mech in self.system.terminalMechanisms.mechanisms):
                    # If MonitoredOutputStatesOption is PRIMARY_OUTPUT_STATES and outputState is primary, include it 
                    if option_spec is MonitoredOutputStatesOption.PRIMARY_OUTPUT_STATES:
                        if output_state is mech.outputState:
                            self.monitoredOutputStates.append(output_state)
                            continue
                    # If MonitoredOutputStatesOption is ALL_OUTPUT_STATES, include it
                    elif option_spec is MonitoredOutputStatesOption.ALL_OUTPUT_STATES:
                        self.monitoredOutputStates.append(output_state)
                    else:
                        raise EVCError("PROGRAM ERROR: unrecognized specification of kwMonitoredOutputStates for "
                                       "{0} of {1}".
                                       format(output_state_name, mech.name))


        # ASSIGN WEIGHTS AND EXPONENTS

        num_monitored_output_states = len(self.monitoredOutputStates)
        exponents = np.ones(num_monitored_output_states)
        weights = np.ones_like(exponents)

        # Get  and assign specification of exponents and weights for mechanisms or outputStates specified in tuples
        for spec in all_specs:
            if isinstance(spec, tuple):
                object_spec = spec[OBJECT]
                # For each outputState in monitoredOutputStates
                for item in self.monitoredOutputStates:
                    # If either that outputState or its ownerMechanism is the object specified in the tuple
                    if item is object_spec or item.name is object_spec or item.ownerMechanism is object_spec:
                        # Assign the exponent and weight specified in the tuple to that outputState
                        i = self.monitoredOutputStates.index(item)
                        exponents[i] = spec[EXPONENT]
                        weights[i] = spec[WEIGHT]

        self.paramsCurrent[kwExecuteMethodParams][kwExponents] = exponents
        self.paramsCurrent[kwExecuteMethodParams][kwWeights] = weights


        # INSTANTIATE INPUT STATES

        # Instantiate inputState for each monitored state in the list
        # from Functions.MechanismStates.MechanismOutputState import MechanismOutputState
        for monitored_state in self.monitoredOutputStates:
            if isinstance(monitored_state, MechanismOutputState):
                self.instantiate_monitoring_input_state(monitored_state, context=context)
            elif isinstance(monitored_state, Mechanism):
                for output_state in monitored_state.outputStates:
                    self.instantiate_monitoring_input_state(output_state, context=context)
            else:
                raise EVCError("PROGRAM ERROR: outputState specification ({0}) slipped through that is "
                               "neither a MechanismOutputState nor Mechanism".format(monitored_state))

        if self.prefs.verbosePref:
            print ("{0} monitoring:".format(self.name))
            for state in self.monitoredOutputStates:
                exponent = \
                    self.paramsCurrent[kwExecuteMethodParams][kwExponents][self.monitoredOutputStates.index(state)]
                weight = \
                    self.paramsCurrent[kwExecuteMethodParams][kwWeights][self.monitoredOutputStates.index(state)]
                print ("\t{0} (exp: {1}; wt: {2})".format(state.name, exponent, weight))

        self.inputValue = self.variable.copy() * 0.0

        return self.inputStates

# FIX: COMPARE TO SystemControlMechanism VERSION;  IF SAME, MOVE TO SystemControlMechanism
# FIX: ??RENAME AND MODIFY TO OVERRIDE Mechanism.instantiate_input_states
# FIX: ??CAN NOW call super.instantiate_input_states from self.instantiate_input_states (ABOVE)??
    def instantiate_monitoring_input_state(self, monitored_state, context=NotImplemented):
        """Instantiate monitoring inputState, add to self.inputStates, and instantiate projection from monitored_state

        Extend self.variable to accomodate new inputState used to monitor monitored_state
        Instantiate new inputState and add to self.InputStates
        Instantiate Mapping Projection from monitored_state to new inputState

        Args:
            monitored_state (MechanismOutputState):
            context:
        """

        self.validate_monitored_state_spec(monitored_state, context=context)

        state_name = monitored_state.name + '_Monitor'

        # Extend self.variable to accommodate new inputState
        if self.variable is None:
            self.variable = np.atleast_2d(monitored_state.value)
        else:
            self.variable = np.append(self.variable, np.atleast_2d(monitored_state.value), 0)
        variable_item_index = self.variable.size-1

        # Instantiate inputState to receive projection from monitored_state:
        from Functions.MechanismStates.MechanismInputState import MechanismInputState
        input_state = self.instantiate_mechanism_state(
                                        state_type=MechanismInputState,
                                        state_name=state_name,
                                        state_spec=defaultControlAllocation,
                                        constraint_values=np.array(self.variable[variable_item_index]),
                                        constraint_values_name='Default control allocation',
                                        context=context)

        # Instantiate Mapping Projection from monitored_state to new input_state
        from Functions.Projections.Mapping import Mapping
        Mapping(sender=monitored_state, receiver=input_state)

        #  Update inputState and inputStates
        try:
            self.inputStates[state_name] = input_state
        except AttributeError:
            self.inputStates = OrderedDict({state_name:input_state})
            self.inputState = list(self.inputStates)[0]

# # FIX:  FROM MECHANISM / RECONCILE WITH ABOVE:
#         self.inputValue = self.variable.copy() * 0.0
#         # Assign self.inputState to first inputState in dict
#         try:
#             self.inputState = list(self.inputStates.values())[0]
#         except AttributeError:
#             self.inputState = None



    def instantiate_prediction_mechanisms(self, context=NotImplemented):
        """Add prediction Process for each origin (input) Mechanism in System

        Args:
            context:
        """

        from Functions.Process import Process_Base

        # Instantiate a predictionMechanism for each origin (input) Mechanism in self.system,
        #    instantiate a Process (that maps the origin to the prediction mechanism),
        #    and add that Process to System.processes list
        self.predictionMechanisms = []
        self.predictionProcesses = []

        for mech in list(self.system.originMechanisms):

            # Get any params specified for predictionMechanism(s) by EVCMechanism
            try:
                prediction_mechanism_params = self.paramsCurrent[kwPredictionMechanismParams]
            except KeyError:
                prediction_mechanism_params = {}

            # Add outputState with name based on originMechanism
            output_state_name = mech.name + '_' + kwPredictionMechanismOutput
            prediction_mechanism_params[kwMechanismOutputStates] = [output_state_name]

            # Instantiate predictionMechanism
            prediction_mechanism = self.paramsCurrent[kwPredictionMechanismType](
                                                            name=mech.name + "_" + kwPredictionMechanism,
                                                            params = prediction_mechanism_params)
            self.predictionMechanisms.append(prediction_mechanism)

            # Instantiate rocess with originMechanism projecting to predictionMechanism, and phase = originMechanism
            prediction_process = Process_Base(default_input_value=NotImplemented,
                                              params={
                                                  kwConfiguration:[(mech, mech.phaseSpec),
                                                                   kwIdentityMatrix,
                                                                   (prediction_mechanism, mech.phaseSpec)]},
                                              name=mech.name + "_" + kwPredictionProcess
                                              )
            # Add the process to the system's list of processes, and the controller's list of prediction processes
            self.system.processes.append((prediction_process, None))
            self.predictionProcesses.append(prediction_process)

        # Re-instantiate System.graph with predictionMechanism Processes added
        # FIX:  CONFIRM THAT self.system.variable IS CORRECT BELOW:
        self.system.instantiate_graph(self.system.variable, context=context)

    def get_simulation_system_inputs(self, phase):
        """Return array of predictionMechanism values for use as input for simulation run of System

        Returns: 2D np.array

        """
        simulation_inputs = np.empty_like(self.system.inputs)
        for i in range(len(self.predictionMechanisms)):
            if self.predictionMechanisms[i].phaseSpec == phase:
                simulation_inputs[i] = self.predictionMechanisms[i].value
            else:
                simulation_inputs[i] = np.atleast_1d(0)
        return simulation_inputs

    def update(self, time_scale=TimeScale.TRIAL, runtime_params=NotImplemented, context=NotImplemented):
        """Construct and search space of control signals for maximum EVC and set value of outputStates accordingly

        Get allocationSamples for the ControlSignal Projection for each outputState in self.outputStates
        Construct self.controlSignalSearchSpace (2D np.array, each item of which is a permuted set of samples):
        Call self.system.execute for each combination of ControlSignals in self.controlSignalSearchSpace
        Store the vector of values for monitored states (inputStates in self.inputStates) for each combination
        Call self.execute to calculate the EVC for each vector, identify the maxium, and assign to self.EVCmax
        Set EVCmaxPolicy to combination of ControlSignal allocations (outputState.values) corresponding to EVCmax
        Set value for each outputState (allocation for each ControlSignal) to the values in self.EVCmaxPolicy
        Return EVCmax

         Note:
         * runtime_params is used for self.execute (that calculates the EVC for each call to system.execute);
             it is NOT used for system.execute — that uses the runtime_params
              provided for the Mechanisms in each Process.congiruation

        Args:
            time_scale:
            runtime_params:
            context:

        Returns (2D np.array): value of outputState for each monitored state (in self.inputStates) for EVCMax
        """

        #region CONSTRUCT SEARCH SPACE
        # IMPLEMENTATION NOTE: MOVED FROM instantiate_execute_method
        #                      TO BE SURE LATEST VALUES OF allocationSamples ARE USED (IN CASE THEY HAVE CHANGED)
        #                      SHOULD BE PROFILED, AS MAY BE INEFFICIENT TO EXECUTE THIS FOR EVERY RUN
        control_signal_sampling_ranges = []
        # Get allocationSamples for all ControlSignal Projections of all outputStates in self.outputStates
        num_output_states = len(self.outputStates)

        for output_state in self.outputStates:
            for projection in self.outputStates[output_state].sendsToProjections:
                control_signal_sampling_ranges.append(projection.allocationSamples)

        # Construct controlSignalSearchSpace:  set of all permutations of ControlSignal allocations
        #                                     (one sample from the allocationSample of each ControlSignal)
        # Reference for implementation below:
        # http://stackoverflow.com/questions/1208118/using-numpy-to-build-an-array-of-all-combinations-of-two-arrays
        self.controlSignalSearchSpace = \
            np.array(np.meshgrid(*control_signal_sampling_ranges)).T.reshape(-1,num_output_states)
        # END MOVE
        #endregion

        #region ASSIGN SIMULATION INPUT(S)
        # For each prediction mechanism, assign its value as input to corresponding process for the simulation
        for mech in self.predictionMechanisms:
            # For each outputState of the predictionMechanism, assign its value as the value of the corresponding
            # Process.inputState for the origin Mechanism corresponding to mech
            for output_state in mech.outputStates:
                for input_state_name, input_state in list(mech.inputStates.items()):
                    for projection in input_state.receivesFromProjections:
                        input = mech.outputStates[output_state].value
                        projection.sender.ownerMechanism.inputState.receivesFromProjections[0].sender.value = input

        #endregion

        #region RUN SIMULATION

        self.EVCmax = 0 # <- FIX:  IS THIS THE RIGHT INITIAL VALUE?  OR SHOULD IT BE MAXIMUM NEGATIVE VALUE?
        self.EVCvalues = []
        self.EVCpolicies = []

        # Reset context so that System knows this is a simulation (to avoid infinitely recursive loop)
        context = context.replace('EXECUTING', '{0} {1}'.format(self.name, kwEVCSimulation))

        if self.prefs.reportOutputPref:
            progress_bar_rate_str = ""
            search_space_size = len(self.controlSignalSearchSpace)
            progress_bar_rate = int(10 ** (np.log10(search_space_size)-2))
            if progress_bar_rate > 1:
                progress_bar_rate_str = str(progress_bar_rate) + " "
            print("\n{0} evaluating EVC for {1} (one dot for each {2}of {3} samples): ".
                  format(self.name, self.system.name, progress_bar_rate_str, search_space_size))

        # Evaluate all combinations of controlSignals (policies)
        sample = 0
        self.EVCmaxStateValues = self.variable.copy()
        self.EVCmaxPolicy = self.controlSignalSearchSpace[0] * 0.0

        # IMPLEMENTATION NOTE:  PARALLELIZATION
        #  import multiprocessing module, Pool function
        # implement for loop below as function
        # create pnl_pool = Pool()
        # call pool with function to get results:
        #     results = Pool.map(<pnl function>, <range>)
        # call function using multiprocessing.pool
        # produces list that I reduce using objective to generate the max

        # IMPLEMENTATION NOTE:  consider optimizing this (using pybind11??)  xxx

        if PARALLELIZE:
            EVC_pool = Pool()
            results = EVC_pool.map(compute_EVC, [(self, True, arg, runtime_params, time_scale, context)
                                                 for arg in self.controlSignalSearchSpace])

        else:
            Comm = MPI.COMM_WORLD
            rank = Comm.Get_rank()
            print("Rank: ", rank)
            size = Comm.Get_size()

            chunk_size = (len(self.controlSignalSearchSpace) + (size-1)) // size
            start = chunk_size * rank
            end = chunk_size * (rank+1)
            if end > len(self.controlSignalSearchSpace):
                end = len(self.controlSignalSearchSpace)

            # start = 0
            # end = len(self.controlSignalSearchSpace)
            result = None
            # print(self.controlSignalSearchSpace.shape)
            print("START: {0}\nEND: {1}".format(start,end))
            # for allocation_vector in self.controlSignalSearchSpace:
            for allocation_vector in self.controlSignalSearchSpace[start:end,:]:
            # for allocation_index in range(start,end):
            #     allocation_vector = self.controlSignalSearchSpace[allocation_index,0]

                if self.prefs.reportOutputPref:
                    increment_progress_bar = (progress_bar_rate < 1) or not (sample % progress_bar_rate)
                    if increment_progress_bar:
                        print(kwProgressBarChar, end='', flush=True)
                sample +=1

                # MODIFIED 7/19/16 NEW:
                result = compute_EVC(args=(self, False, allocation_vector, runtime_params, time_scale, context))

            results = Comm.allgather(result)

            # DO LOCAL REDUCE HERE

            # FROM MIKE (INITIAL VERSION)
            # a = np.random.random()
            # mymax=Comm.allreduce(a, MPI.MAX)
            # print(mymax)

    # FIX: ?? NEED TO SET OUTPUT VALUES AND RUN SYSTEM AGAIN?? OR JUST:
    # FIX:      - SET values for self.inputStates TO EVCMax ??
    # FIX:      - SET values for self.outputStates TO EVCMaxPolicy ??
    # FIX:  ??NECESSARY:
        if self.prefs.reportOutputPref:
            print("\nEVC simulation completed")
#endregion

        #region ASSIGN CONTROL SIGNALS

        # Assign allocations to controlSignals (self.outputStates) for optimal allocation policy:
        for i in range(len(self.outputStates)):
            list(self.outputStates.values())[i].value = np.atleast_1d(self.EVCmaxPolicy[i])

        # Assign max values for optimal allocation policy to self.inputStates (for reference only)
        for i in range(len(self.inputStates)):
            list(self.inputStates.values())[i].value = np.atleast_1d(self.EVCmaxStateValues[i])

        # Report EVC max info
        if self.prefs.reportOutputPref:
            print ("\nMaximum EVC for {0}: {1}".format(self.system.name, float(self.EVCmax)))
            print ("ControlSignal allocations for maximum EVC:")
            for i in range(len(self.outputStates)):
                print("\t{0}: {1}".format(list(self.outputStates.values())[i].name,
                                        self.EVCmaxPolicy[i]))
            print()
        #endregion

        return self.EVCmax

    # IMPLEMENTATION NOTE: NOT IMPLEMENTED, AS PROVIDED BY params[kwExecuteMethod]
    # def execute(self, params, time_scale, context):
    #     """Calculate EVC for values of monitored states (in self.inputStates)
    #
    #     Args:
    #         params:
    #         time_scale:
    #         context:
    #     """
    #
    #     return
    #
    #


    def add_monitored_states(self, states_spec, context=NotImplemented):
        """Validate and then instantiate outputStates to be monitored by EVC

        Use by other objects to add a state or list of states to be monitored by EVC
        states_spec can be a Mechanism, MechanismOutputState or list of either or both
        If item is a Mechanism, each of its outputStates will be used
        All of the outputStates specified must be for a Mechanism that is in self.System

        Args:
            states_spec (Mechanism, MechanimsOutputState or list of either or both:
            context:
        """
        states_spec = list(states_spec)
        self.validate_monitored_state_spec(states_spec, context=context)
        # FIX: MODIFIED 7/18/16:  NEED TO IMPLEMENT  instantiate_monitored_output_states SO AS TO CALL instantiate_input_states()
        self.instantiate_monitored_output_states(states_spec, context=context)

    def inspect(self):

        print ("\n---------------------------------------------------------")

        print ("\n{0}".format(self.name))
        print("\n\tMonitoring the following mechanism outputStates:")
        for state_name, state in list(self.inputStates.items()):
            for projection in state.receivesFromProjections:
                monitored_state = projection.sender
                monitored_state_mech = projection.sender.ownerMechanism
                monitored_state_index = self.monitoredOutputStates.index(monitored_state)
                exponent = self.paramsCurrent[kwExecuteMethodParams][kwExponents][monitored_state_index]
                weight = self.paramsCurrent[kwExecuteMethodParams][kwWeights][monitored_state_index]
                print ("\t\t{0}: {1} (exp: {2}; wt: {3})".
                       format(monitored_state_mech.name, monitored_state.name, exponent, weight))

        print ("\n\tControlling the following mechanism parameters:".format(self.name))
        for state_name, state in list(self.outputStates.items()):
            for projection in state.sendsToProjections:
                print ("\t\t{0}: {1}".format(projection.receiver.ownerMechanism.name, projection.receiver.name))

        print ("\n---------------------------------------------------------")


def compute_EVC(args):
    """compute EVC

    Args:
        ctlr (EVCMechanism)

    Returns: XXX???

    """

    ctlr, parallel, allocation_vector, runtime_params, time_scale, context = args

    # Implement the current policy over ControlSignal Projections
    for i in range(len(ctlr.outputStates)):
        list(ctlr.outputStates.values())[i].value = np.atleast_1d(allocation_vector[i])

    # Execute self.system for the current policy
    for i in range(ctlr.system.phaseSpecMax+1):
        CentralClock.time_step = i
        simulation_inputs = ctlr.get_simulation_system_inputs(phase=i)
        ctlr.system.execute(inputs=simulation_inputs, time_scale=time_scale, context=context)

    # Get control cost for this policy
    # Iterate over all outputStates (controlSignals)
    for i in range(len(ctlr.outputStates)):
        # Get projections for this outputState
        output_state_projections = list(ctlr.outputStates.values())[i].sendsToProjections
        # Iterate over all projections for the outputState
        for projection in output_state_projections:
            # Get ControlSignal cost
            control_signal_cost = np.atleast_2d(projection.cost)
            # Build vector of controlSignal costs
            if i==0:
                control_signal_costs = np.atleast_2d(control_signal_cost)
            else:
                control_signal_costs = np.append(control_signal_costs, control_signal_cost, 0)

    total_current_control_costs = ctlr.paramsCurrent[kwCostAggregationFunction].execute(control_signal_costs)

    variable = []
    for input_state in list(ctlr.inputStates.values()):
        variable.append(input_state.value)
    variable = np.atleast_2d(variable)

    # Get value of current policy = weighted sum of values of monitored states
    # Note:  self.variable = value of monitored states (self.inputStates)
    ctlr.update_input_states(runtime_params=runtime_params, time_scale=time_scale,context=context)
    total_current_value = ctlr.execute(variable=ctlr.variable,
                                       params=runtime_params,
                                       time_scale=time_scale,
                                       context=context)

    # Calculate EVC for the result (default: total value - total cost)
    EVC_current = ctlr.paramsCurrent[kwCostApplicationFunction].execute([total_current_value,
                                                                         -total_current_control_costs])

    if parallel:
        return

    else:
        ctlr.EVCmax = max(EVC_current, ctlr.EVCmax)

        # Add to list of EVC values and allocation policies if save option is set
        if ctlr.paramsCurrent[kwSaveAllPoliciesAndValues]:
            ctlr.EVCvalues.append(EVC_current)
            ctlr.EVCpolicies.append(allocation_vector.copy())

        # If EVC is greater than the previous value:
        # - store the current set of monitored state value in EVCmaxStateValues
        # - store the current set of controlSignals in EVCmaxPolicy
        if ctlr.EVCmax > EVC_current:
            ctlr.EVCmaxStateValues = ctlr.variable.copy()
            ctlr.EVCmaxPolicy = allocation_vector.copy()


# FIX: ?? NEED TO SET OUTPUT VALUES AND RUN SYSTEM AGAIN?? OR JUST:
# FIX:      - SET values for self.inputStates TO EVCMax ??
# FIX:      - SET values for self.outputStates TO EVCMaxPolicy ??
# FIX:  ??NECESSARY:

