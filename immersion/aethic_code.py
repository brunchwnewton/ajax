import copy
from typing import Optional, Any, Union
from itertools import chain, combinations


class State:
    """
    Represents an algebraic state with an associated weight.

    This class implements a Ring-like structure where a specific instance
    (BLANK) serves as the additive identity (Zero). This canonical Zero
    is strictly unique (Singleton) and is auto-resolved whenever a state
    is instantiated with zero weight or None state.

    Attributes:
        BLANK (State): The canonical Singleton instance representing a
                       null/zero state. It is an instance of UnweightedState.
    """

    # The canonical zero element (Singleton).
    # Populated lazily on first access to avoid import/definition loops.
    BLANK: Optional['State'] = None

    def __new__(cls, state: Union[object, 'State'], weight: float = 0):
        """
        Allocator that enforces the Singleton pattern for the Zero state.
        Also handles unpacking logic for copy-construction.
        """
        # 1. Unpack State objects if passed (Copy-Constructor Logic)
        # We must look inside the wrapper to check the actual content.
        if isinstance(state, State):
            if state is State.BLANK:
                state_content = None
            else:
                state_content = state.state
        else:
            state_content = state

        # 2. Logic Check: Does this request resolve to the Zero/Blank element?
        # If the content is None or the requested weight is 0, this is a Zero.
        if state_content is None or weight == 0:

            # Lazy Initialization: Create the BLANK if it doesn't exist.
            if State.BLANK is None:
                # CRITICAL: Use object.__new__ to allocate memory directly.
                # This bypasses State.__new__ to prevent infinite recursion.
                State.BLANK = object.__new__(UnweightedState)

                # Manually initialize internal storage
                State.BLANK.__dict__['state'] = None
                State.BLANK.__dict__['_weight'] = 0.0

            return State.BLANK

        # 3. Standard Allocation: Proceed with normal object creation.
        return super().__new__(cls)

    def __init__(self, state: Union[object, 'State'], weight: float):
        """
        Initializes the state.
        Handles copy-construction from existing State objects.
        """
        # GUARD CLAUSE: Python automatically calls __init__ on the object
        # returned by __new__. If __new__ returned the canonical BLANK,
        # we must return immediately to prevent overwriting its zero weight.
        if self is State.BLANK:
            return

        # Unwrapping Logic:
        # Ensure we store the underlying data, not a nested State object.
        if isinstance(state, State):
            self.state = state.state
        else:
            self.state = state

        self._weight = weight

    def __eq__(self, other: Any) -> bool:
        """
        Allows using '==' to compare states.
        Two states are equal if they have the same state content AND same weight.
        """
        if not isinstance(other, State):
            return NotImplemented
        return self.state == other.state and self._weight == other._weight

    def __mul__(self, factor: Any):
        if factor == 0:
            return type(self)(None, 0)

        if self is type(self).BLANK:
            return type(self).BLANK

        result = copy.copy(self)
        result._weight *= factor

        if result._weight == 0:
            return type(self)(None, 0)

        return result

    def __rmul__(self, factor: float):
        return self.__mul__(factor)

    def __add__(self, other: Any):
        """
        Adds two states together.

        Rules:
        1. 0 + State = State (Identity property)
        2. State A + State A = State A (with weights summed)
        3. State A + State B = ValueError (Incompatible states)
        """
        # Allow addition with literal 0 (useful for Python's sum() function)
        if other == 0:
            return self

        if not isinstance(other, State):
            return NotImplemented

        # Rule 1: Handle the Identity (Zero/BLANK) cases
        if self is type(self).BLANK:
            return other
        if other is type(self).BLANK:
            return self

        # Rule 3: Check Compatibility
        if self.state != other.state:
            raise ValueError(
                f"Cannot add states with different configurations: '{self.state}' vs '{other.state}'"
            )

        # Rule 2: Perform Addition
        # Note: If weights sum to 0, State() automatically returns BLANK
        return type(self)(self.state, self._weight + other._weight)

    def __radd__(self, other: Any):
        """
        Supports reverse addition, e.g., sum([s1, s2]) which starts with 0.
        """
        return self.__add__(other)

    def __sub__(self, other: Any):
        """
        Subtracts one state from another.
        Implemented as: Self + (-1 * Other)
        """
        # 1. Identity Check (State - 0 = State)
        if other == 0 or other is type(self).BLANK:
            return self

        # 2. Zero Check (0 - State = -State)
        if self is type(self).BLANK:
            return other * -1.0

        # 3. Standard Subtraction
        # We delegate to __add__ to reuse the state compatibility checks
        return self + (other * -1.0)

    def __rsub__(self, other: Any):
        """
        Supports reverse subtraction (e.g., 0 - State).
        Note: 'State - 0' is handled by __sub__.
        """
        # If we are here, 'other' is likely 0 (from sum() or similar)
        # because if 'other' was a State, __sub__ would have been called.
        if other == 0:
            return self * -1.0

        return NotImplemented

    def __repr__(self) -> str:
        return f"State(state={self.state}, weight={self._weight})"

    @staticmethod
    def make_unweighted(instance: 'State') -> 'UnweightedState':
        """
        Factory that returns a new UnweightedState based on the input's state.
        This effectively 'normalizes' the weight to 1 (unless it's BLANK).
        """
        # If the input is already BLANK, returning a new UnweightedState(None)
        # will just return BLANK again, which is correct.
        return UnweightedState(instance.state)

    @classmethod
    def zero(cls) -> 'State':
        """Safely returns the canonical BLANK state."""
        return cls(None, 0)

    @property
    def weight(self) -> float:
        """ReadOnly access to the weight."""
        return self._weight

    @weight.setter
    def weight(self, value: float):
        """Prevents modifying the weight of the BLANK state."""
        if self is State.BLANK:
            raise AttributeError("Cannot modify the weight of the canonical BLANK state.")
        self._weight = value


class UnweightedState(State):
    """
    A specialized State factory that defaults to a weight of 1.
    """

    def __new__(cls, state: Union[object, 'State'], weight: float = 1.0):
        # OVERRIDE: We must explicitly default weight to 1.0 here.
        # If we used State.__new__'s default (0), this would incorrectly
        # resolve to BLANK during allocation.
        return super().__new__(cls, state, weight)

    def __init__(self, state: Union[object, 'State'], weight: float = None):
        if self is State.BLANK:
            return

        # Super init handles the unwrapping of 'state'
        # We hardcode 1.0 to enforce the unweighted behavior
        super().__init__(state, 1.0)


class Attribute:
    """The class of Aethic attribute and its mathematical structure.

    An attribute consists of:
    1. An identifier (distinguishes attributes)
    2. A class (the set of possible states)
    3. A relation set (connections to other attributes)
    """

    def __init__(self, identity, states_list: list[State], relation_set: dict):
        self.identity = identity
        self.states_list = states_list
        self.relation_set = relation_set

    def set_of_all_states(self):
        """Returns all possible states this attribute can take."""
        return self.states_list

    def pull_logical_implications(self, state: State, other_info: dict[object, State]):
        """Given an Attribute and specific other info, generate all possible,
        as will be stored in the Attribute's relation set, however semantically vast."""

        implied_list = self.relation_set.get((state, other_info), None)
        return implied_list


class Retrieval:
    """The class of Aethic retrieval and its mathematical structure.

    A retrieval represents the result of querying an Aethus for
    the state of a particular attribute. It may contain:
    - A single state (when attribute is present)
    - Multiple states (when in superposition)
    - Empty (when attribute is None)
    """

    def __init__(self, states):
        self.states = states

    def __mul__(self, other):
        """Retrieval multiplication represents attribute conjunction."""
        return Retrieval(self.states + other.states)


class Aethus(State):
    """The mathematical structure of the Aethus.

    An Aethus is an equivalence class over sets of stated-attributes,
    representing the complete informational state of a system.
    """

    HYPERINVALID_AETHUS: Optional['State'] = None

    def __new__(cls, state: Union[dict, 'State'], weight: float = 1.0, close=True):
        # Similar defaulting to weight of one as
        # initialization for unweighted state

        if Aethus.HYPERINVALID_AETHUS is None:
            # CRITICAL: Use object.__new__ to allocate memory directly.
            # This bypasses State.__new__ to prevent infinite recursion.
            Aethus.HYPERINVALID_AETHUS = object.__new__(UnweightedState)

            # Manually initialize internal storage
            Aethus.HYPERINVALID_AETHUS.__dict__['state'] = "Invalid"

        return super().__new__(cls, state, weight)

    def __init__(self, state: Union[dict, 'State'], weight: float = None, close=True):
        if self is State.BLANK:
            return

        # Super init handles the unwrapping of 'state'
        super().__init__(state, 1.0)

        self._attributes = Aethus.logical_closure(state) if close else state

    @classmethod
    def logical_closure(cls, static_aethus: dict[Attribute, State]):
        """Carry out exhaustive Aethic logical closure, meaning the generation
        of a 3-Aethus from an arbitrary 2-Aethus.

        This is why Attribute objects must be fully semantically well-defined,
        which may be far beyond the abilities of a human, and is rather more like
        a full LLM vector embedding database.
        """

        def dict_powerset(d):
            # Convert items to a list: [('A', 1), ('B', 2), ...]
            items = list(d.items())

            # Generate all combinations of all lengths (from 0 to N)
            # chain.from_iterable flattens the list of combinations
            all_combos = chain.from_iterable(combinations(items, r) for r in range(len(items) + 1))

            # Convert each combination back into a dict
            return [dict(combo) for combo in all_combos]

        # ...Implied abstract processing first...

        return static_aethus

    def get(self, key, default=State.BLANK):
        # Delegating to the internal dict's get method
        return self._attributes.get(key, default)

    def __getitem__(self, key):
        # Direct access: raises KeyError if missing (Standard Python behavior)
        return self._attributes[key]

    def keys(self):
        return self._attributes.keys()

    def is_null_aethus(self) -> bool:
        for attr in self.keys():
            if self.get(attr) is not State.BLANK:
                return False
        return True

    def is_present(self, attribute: Attribute) -> bool:
        """Check if attribute has a definite state in this Aethus."""
        return self.get(attribute) is not State.BLANK

    def is_nonpresent(self, attribute: Attribute) -> bool:
        """Check if attribute is blank (unknown) in this Aethus."""
        for state in attribute.set_of_all_states():
            if not self.aethic_union(Aethus({attribute: state})).is_null_aethus():
                return False
        return True

    def is_mixed_decomposable(self, attribute: Attribute):
        return not (self.is_present(attribute) or self.is_nonpresent(attribute))

    def get_proper_children(self):
        # THIS CODE IS UNFINISHED
        pass

    def aethic_union(A, B, unweighted=False):
        """Compute the Aethic union of two Aethae.
        """
        result_attributes = {}

        # Get all attributes from both Aethae
        all_attrs = set(A.keys()) | set(B.keys())

        conditions = 1

        for attr in all_attrs:
            state_A = A.get(attr, State.BLANK)
            state_B = B.get(attr, State.BLANK)

            unit_A, unit_B = UnweightedState(state_A), UnweightedState(state_B)
            if unweighted:
                state_A, state_B = unit_A, unit_B

                if state_A == state_B:
                    # SAME state: preserved in union (agreeing)
                    result_attributes[attr] = state_A
                else:
                    # DIFFERENT states: becomes blank (superposition)
                    # This is the source of quantum superposition
                    result_attributes[attr] = State.BLANK
            else:
                if unit_A == unit_B:
                    result_attributes[attr] = state_A + state_B
                else:
                    set_state = None
                    if state_A.weight == state_B.weight:
                        set_state = State.BLANK
                    elif state_A.weight > state_B.weight:
                        set_state = State(state_A, state_A.weight - state_B.weight)
                    else:
                        set_state = State(state_B, state_B.weight - state_A.weight)

                    result_attributes[attr] = set_state
                    conditions *= Aethus.limit_superposition(attr, state_A, state_B)

        return Aethus(result_attributes) * conditions

    def unweighted_aethic_union(A, B):
        """Compute the Aethic union of two Aethae.

        The Union Principle: Combines two Aethae such that only
        attributes present with the SAME state in both are preserved.
        Differing attributes become blank (superposed).

        This is the fundamental operation for creating superpositions.

        Rather than extending to the weighted Aethic union, this instead is
        the last-common ancestor operation of the Aethic tree.
        """
        return A.aethic_union(B, unweighted=True)

    def aethic_intersection(A, B, unweighted=False):
        """Compute the Aethic intersection of two Aethae.

        Forces all attributes into coexistence, but may produce
        invalid Aethae if states are contradictory.
        """
        result_attributes = {}

        all_attrs = set(A.keys()) | set(B.keys())

        coefficient = 1

        for attr in all_attrs:
            state_A = A.get(attr, State.BLANK)
            state_B = B.get(attr, State.BLANK)

            if unweighted:
                state_A, state_B = UnweightedState(state_A), UnweightedState(state_B)

            if state_A == State.BLANK:
                result_attributes[attr] = state_B
            elif state_B == State.BLANK:
                result_attributes[attr] = state_A
            elif state_A == state_B:
                result_attributes[attr] = state_A if unweighted else State(state_A, state_A.weight * state_B.weight)
            else:
                # Contradiction: intersection may be invalid
                # Append hyperinvalid Aethus
                coefficient *= Aethus.HYPERINVALID_AETHUS

        return Aethus(result_attributes) * coefficient

    def split(self, attribute):
        """Apply Aethic Dichotomy Theorem to decompose attribute."""

        # THIS CODE IS UNFINISHED
        return None, None

    def has_parent(self, parent):
        """Tests if an Aethus is a parent to another.

        An Aethus is a parent of another if it is Aethically equivalent
        to their unweighted union.
        """
        return parent == self.unweighted_aethic_union(parent)

    def retrieve(self, attribute: Attribute):
        """Core retrieval operation implementing the Three Postulates.

        This is the fundamental operation of Aethic reasoning,
        determining how information is accessed from an Aethus.
        """
        if self.is_present(attribute):
            # CASE 1: Simple lookup - attribute has definite state
            return Retrieval(self[attribute])

        elif self.is_nonpresent(attribute):
            # CASE 2: Second Postulate of the Aethus
            # Unknown attributes return ALL possible states
            # This is the source of agreeing superpositions
            return Retrieval(attribute.set_of_all_states())

        elif attribute is None:
            # CASE 3: Null attribute retrieves nothing
            return Retrieval([])

        else:
            # CASE 4: Application of Aethic Dichotomy Theorem
            # Split into present and blank components
            interior, exterior = self.split(attribute)

            # Retrieval multiplication is attribute conjunction
            return self.retrieve(interior) * self.retrieve(exterior)

    def __mul__(self, other) -> 'Aethus':
        if isinstance(other, float) or isinstance(other, int):
            return super().__mul__(other)

        return self.aethic_intersection(other)

    def __rmul__(self, other) -> 'Aethus':
        return self.__mul__(other)

    def __add__(self, other) -> 'Aethus':
        if isinstance(other, float) or isinstance(other, int):
            return super().__add__(other)

        return self.aethic_union(other)

    def __radd__(self, other) -> 'Aethus':
        return self.__add__(other)

    @classmethod
    def limit_superposition(cls, attr, *allowed_states):
        """Create an Aethus with a conditional attribute.

        Form the minimal Aethus for which the state of a preset attribute
        holding any state besides the allowed ones is taken as invalid.
        Primarily of use for being intersected to other Aethae.

        Args:
            attr: The constraining attribute
            *allowed_states: The window of allowable states.

        Returns:
            The conditional Aethus defined by limiting to these allowed
            states only under this attribute.
        """
        # THIS CODE IS UNFINISHED
        pass


def take_reduced_form(A: Aethus) -> Aethus | None:
    """Gather the reduced form of an Aethus.

    The reduced form R is the last common parent Aethus
    of precisely all proper children B of A with no invalid children C.

    If no such Aethae B exist, then A has no reduced form, so we return None.
    """
    valid_combo = []
    children_B = A.get_proper_children()

    for b_node in children_B:
        # We need to determine if this specific B leads to *any* invalid C
        b_leads_to_invalid_c = False
        children_C = b_node.get_proper_children()

        for c_node in children_C:
            if not is_valid_aethus(c_node):
                b_leads_to_invalid_c = True
                break  # Found the 'bad' C for this B

        # Each satisfactory proper child is incorporated
        if not b_leads_to_invalid_c:
            valid_combo.append(b_node)

    if not valid_combo:
        # List is empty
        return None  # No reduced form exists
        # Statement of third postulate: this makes A invalid
    else:
        # Return the correct reduced form as the unweighted Aethic union
        # That is, the last-common ancestor of all satisfactory B
        result = valid_combo.pop(0)
        for item in valid_combo:
            result = result.unweighted_aethic_union(item)
        return result


def third_postulate_satisfied(A: Aethus) -> bool:
    """Check if the Third Postulate is satisfied.

    Returns False if and only if:
    For ALL children B of A, there exists ANY child C of B such that
    is_valid_aethus(C) is False.

    Otherwise, returns True (including the edge case where A has no children).
    """
    return take_reduced_form(A) is not None


def has_disjoint_states(A: Aethus) -> bool:
    """Determines if Aethus holds disjoint stated-attributes.

    Having disjoint stated-attributes is logically equivalent to
    being a child Aethus to the hyperinvalid Aethus.
    """
    return A.has_parent(Aethus.HYPERINVALID_AETHUS)


def is_valid_aethus(A: Aethus) -> bool:
    """Deterministic algorithm to validate an Aethus.

    The ability to invalidate Aethae is fundamental to Aethic
    reasoning's predictive power. Invalid Aethae encode material
    implication: A → B becomes "A ∧ ¬B is invalid Aethus."
    """

    # Check all stated-attributes for internal consistency
    if has_disjoint_states(A):
        return False

    # Apply Third Postulate checks
    if not third_postulate_satisfied(A):
        return False

    return True


def enumerate_state_combinations(A: Aethus, beta: Attribute):
    # THIS CODE IS UNFINISHED
    pass


def general_solution(A: Aethus, beta: Attribute) -> Retrieval:
    """General Analytic Solution Algorithm for the Measurement Problem.

    Args:
        A: The empirical Aethus corresponding to the system's reality
        beta: An Aethic Template to retrieve the state of

    Returns:
        An exact mapping between parameters and allowed Aethic outcomes.
        Renders wavefunction collapse as algorithmic.
    """

    # STEP 1: Check if beta is present (definite state)
    if A.is_present(beta):
        B = A.query_state(beta)
        return B  # Simple case: direct lookup

    # STEP 2: We know beta is in superposition
    # Decompose into present and impartially blank components
    beta_present, beta_blank = A.split(beta)

    # STEP 3: Handle the impartially blank case
    if A.is_impartially_blank(beta):

        if A.is_uncertainty_principle(beta):
            # Case 3a: Aethic uncertainty principle applies
            # Second Postulate: blank → agreeing superposition
            return Retrieval(
                states=beta.set_of_all_states(),
                weights=A.get_weights(beta)
            )

        else:
            # Case 3b: Third Postulate applies
            # Conceptually blank would be invalid Aethus

            # Enumerate all possible state combinations
            possible_cases = enumerate_state_combinations(A, beta)

            # Apply Third Postulate to invalidate cases
            valid_cases = []
            for case in possible_cases:
                if third_postulate_satisfied(case):
                    valid_cases.append(case)

            # Remaining valid cases go into agreeing superposition
            # (by Second Postulate, since which case is unknown)
            # This induces DISAGREEING superposition at state level
            return Retrieval(
                states=valid_cases
            )

    # STEP 4: Partial presence - apply dichotomy theorem
    return (general_solution(A, beta_present) *
            general_solution(A, beta_blank))
