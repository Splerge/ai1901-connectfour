"""Spencer and Josh's agent for playing Connect 4."""
import time
import numpy as np
from connectfour.board import Board
from connectfour.agents.computer_player import RandomAgent


PLAYER_ONE_ID = 1
PLAYER_TWO_ID = 2

def get_current_player(num_moves):
    """Counts the moves and returns player 1 if move count is even, returns player 2 if odd"""
    if(num_moves % 2 == 0 or num_moves == 0):
        return PLAYER_ONE_ID
    return PLAYER_TWO_ID

def debug_print_board(board, score=None):
    """Prints out the board argument into the terminal, followed by a newline."""
    string = ""
    for row in board.board:
        for cell in row:
            string += str(cell)
        string += str("\n")
    if score:
        string += str("\nScore: " + str(score))
    print(string)


def count_moves(board):
    """counts the amount of tokens that have been inserted into the board."""
    sum_of_moves = 0
    for i in range(board.height):
        for j in range(board.width):
            if board.board[i][j] != 0:
                sum_of_moves += 1

    return sum_of_moves


def valid_moves_wrapper(board):
    """Wrap the board.valid_moves() generator in our own organiser that
    orders the moves centre to outside, going right first if it is uneven."""

    #this optimisation is specific to 6*7 boards, if it isn't 7 wide then abort.
    if board.width != 7:
        return board.valid_moves()

    list_valid_moves = list(board.valid_moves())
    #this is all hardcoded so no additional calculations need to be made.
    cols = [3, 4, 2, 5, 1, 6, 0]
    for col in cols:
        try:
            yield list_valid_moves[col]
        except IndexError: #this is faster than checking length of the list
            continue

    return board.valid_moves()



def valid_non_losing_moves(board, num_moves):
    # pylint: disable=E1101
    """
    returns: a generator of moves that don't cause a loss the turn after

    board: the node/game state to check
    num_moves: the amount of moves to get to this point
    """
    current_player = get_current_player(num_moves)
    other_player = get_current_player(num_moves+1)

    valid_moves = valid_moves_wrapper(board)
    #loop through each move
    for move in valid_moves:
        my_move = next_state_fast(board, current_player, move)
        winner_num = my_move.winner()
        #if we win then this is a valid move that won't cause us to lose,
        #and there is no reason to continue the search either.
        if winner_num != 0:
            yield move
            break
        enemy_valid_moves = my_move.valid_moves()
        failure = False
        #loop through the enemy's moves after our move.
        #if there is a single move that they can make in which they can win,
        #this whole move of ours is a bust, so don't yield it.
        for enemy_move in enemy_valid_moves:
            node_after = next_state_fast(my_move, other_player, enemy_move)
            winner_num = node_after.winner()
            if winner_num != 0:
                failure = True
                break
        if not failure:
            yield move

def count_non_losing_moves(board, num_moves):
     # pylint: disable=E1101
    """
    I made this method because I feel that that the
    count_non_losing_moves() generator method is inappropriate.
    returns: a sum of moves that don't cause an immediate loss

    board: the node/game state to check
    num_moves: the amount of moves to get to this point
    """
    current_player = get_current_player(num_moves)
    other_player = get_current_player(num_moves+1)

    valid_moves = valid_moves_wrapper(board)
    sum_of_moves = 0
    #loop through each move
    for move in valid_moves:
        my_move = next_state_fast(board, current_player, move)
        winner_num = my_move.winner()
        #if we win then this is a valid move that won't cause us to lose,
        #and there is no reason to continue the search either,
        #we can safely return -one so that the algorithm understands that it can win.
        if winner_num != 0:
            return -1
        enemy_valid_moves = my_move.valid_moves()
        failure = False
        #loop through the enemy's moves after our move.
        #if there is a single move that they can make in which they can win,
        #this whole move of ours is a bust, so don't yield it.
        for enemy_move in enemy_valid_moves:
            node_after = next_state_fast(my_move, other_player, enemy_move)
            winner_num = node_after.winner()
            if winner_num != 0:
                failure = True
                break

        if not failure:
            sum_of_moves += 1
    return sum_of_moves

class Empty(object):
    """hack to avoid _build_winning_zones_map in the board class code"""

def next_state_fast(board, player_id, move):
    """My monkey patching method to avoid using deepcopy and _build_winning_zones_map
    this hack skips the constructor in the board class,
    hence the pylint suppressor"""
    next_board = Empty()
    next_board.__class__ = Board
    #pylint: disable=W0201
    next_board.width = 7
    next_board.height = 6
    next_board.num_to_connect = 4
    next_board.board = [x[:] for x in [[0] * 7] * 6] # superfast way to declare 2d array
    for i in range(board.height):
        for j in range(board.width):
            next_board.board[i][j] = board.board[i][j]
    next_board.board[move[0]][move[1]] = player_id
    next_board.next_state_fast = next_state_fast
    return next_board

 # pylint: disable=too-many-instance-attributes
class StudentAgent(RandomAgent):
    """Our agent class."""
    def __init__(self, name):
        super().__init__(name)
        self.max_depth = -1
        self.id = -1
        self.dimensions = -1
        self.enemy_id = -1
        self.debug = False
        self.transpos_table = {}
        self.middle_col = -1
        self.max_score = -1
        self.min_score = -1

    def set_variable_depth(self, num_moves, possible_branches):
        """variable depth to make the algorithm less slow, but still produce good results"""
        if num_moves == 1:
            self.max_depth = 1
            return
        self.max_depth = 3
        if possible_branches < 7:
            self.max_depth = self.max_depth + int(7 - possible_branches)
        if num_moves > 20:
            self.max_depth = 8
        if num_moves > 24:
            self.max_depth = self.dimensions # max

    def get_move(self, board):
        """
        Args:
            board: An instance of `Board` that is the current state of the board.

        Returns:
            A tuple of two integers, (row, col)
        """
        start = time.time()

        board.next_state_fast = next_state_fast
        #check how many moves have occurred so far on this board.
        current_move_number = count_moves(board)


        #check board size
        if self.dimensions == -1:
            self.dimensions = board.width * board.height
            self.middle_col = round((board.width+1)/2)-1
            self.max_score = (self.dimensions + 1) / 2 - 3
            self.min_score = -(self.dimensions) / 2 + 3

        if current_move_number == 0:
            #hardcoded first move because there is no point calculating anything.
            return ((board.height-1), self.middle_col)

        non_losing_moves_count = count_non_losing_moves(board, current_move_number)

        self.set_variable_depth(current_move_number, non_losing_moves_count)

        #check which player this agent is going to be and set it (as in id, will be either 1 or 2)
        if self.id == -1:
            self.id = get_current_player(current_move_number)
            self.enemy_id = get_current_player(current_move_number+1)

        valid_moves = None

        #we lose, concede
        if non_losing_moves_count == 0:
            valid_moves = valid_moves_wrapper(board)
            best_move = next(valid_moves)
            if self.debug:
                print("Placed a piece in (%d, %d)" % (best_move[0], best_move[1]))
                next_node = next_state_fast(board, self.id, best_move)
                debug_print_board(next_node)
            return best_move
        #we only have one available move
        if non_losing_moves_count == 1:
            valid_moves = valid_non_losing_moves(board, current_move_number)
            best_move = next(valid_moves)
            if self.debug:
                print("Placed a piece in (%d, %d)" % (best_move[0], best_move[1]))
                next_node = next_state_fast(board, self.id, best_move)
                debug_print_board(next_node)
            return best_move
        if non_losing_moves_count == 7:
            #get all moves
            valid_moves = valid_moves_wrapper(board)
        else:
            #get a generator of moves that will not cause this player to lose
            valid_moves = valid_non_losing_moves(board, current_move_number)


        vals = []
        moves = []

        for move in valid_moves:
            minimum = int(-(self.dimensions - 1 - current_move_number) / 2)

            maximum = int((self.dimensions + 1 - current_move_number) / 2)
            next_node = next_state_fast(board, self.id, move)
            moves.append(move)

            value = int(self.minimax_alpha_beta(next_node, minimum, maximum, current_move_number))
            if self.debug:
                print("column number: %d, calculated value: %d" % (move[1], value))
            vals.append(value)


        #check if there is at least 1 valid move that won't cause us to lose.
        #If not then we're guaranteed to lose so just pick the first one.
        if vals:
            best_move = moves[vals.index(max(vals))]
        else:
            valid_moves = board.valid_moves()
            best_move = next(valid_moves)


        end = time.time()
        if self.debug:
            print("Took %r seconds to make this move." % (end - start))

        if self.debug:
            next_node = next_state_fast(board, self.id, best_move)
            print("Placed a piece in (%d, %d)" % (best_move[0], best_move[1]))
            debug_print_board(next_node)

        return best_move


    def minimax_alpha_beta(self, board, alpha, beta, num_moves, sign=1, depth=0):
        """returns score of the board position

        board is the game state to evaluate.
        alpha is the alpha value for the current node

        beta is the beta value for the current node

        num_moves is the amount of moves that have been made so far.
        This is used in heuristic calculations as well
        as determining who's turn it is.

        sign is either 1 or -1 depending on whether board's
        last move is our agent's move or the enemy's.
        1 for our move, -1 for enemy move.

        depth is how deep our search has gone so far, beginning at 0 from get_move().
        """




        # no valid moves that won't cause a loss, aka dead end

        sum_of_moves = count_non_losing_moves(board, num_moves)
        if sum_of_moves == 0:
            return sign * -int((self.dimensions - num_moves) / 2)

        #check if this board has a winner and return if it does
        #this is the heuristic of our algorithm.
        #The number it returns is scored on how many moves
        #it would take to guarantee a victory for a perfect player.
        winner_num = board.winner()
        if winner_num != 0:
            return sign * int((self.dimensions - num_moves) / 2)

        if depth == self.max_depth:
            return sign * self.evaluate_board_state(board)

        #detect a draw, once 40 tokens are on the board in a 6*7 game and no one has won already,
        #no one can possibly win now.
        if num_moves >= self.dimensions - 2:
            return 0

        minimum = int(-(self.dimensions - num_moves) / 2)
        if alpha < minimum:
            alpha = minimum
            if alpha >= beta:
                return alpha #prune children.

        # set beta to the maximum possible value
        maximum = int((self.dimensions - num_moves) / 2)
        if beta > maximum:
            beta = maximum
            if alpha >= beta:
                return beta  #prune children.


        valid_moves = valid_moves_wrapper(board)
        vals = []
        if sign == 1:
            value = maximum
            for move in valid_moves:
                next_node = next_state_fast(board, get_current_player(num_moves+1), move)
                # recursively go through the children of this node.
                result = self.minimax_alpha_beta(next_node, alpha, beta, num_moves+1, -sign, depth + 1)
                vals.append(result)

                if result < value:
                    value = result
                if value < beta:
                    beta = value

                if alpha >= beta:
                    break
            return value
        value = minimum
        for move in valid_moves:
            next_node = next_state_fast(board, get_current_player(num_moves+1), move)
            # recursively go through the children of this node.
            result = self.minimax_alpha_beta(next_node, alpha, beta, num_moves+1, -sign, depth + 1)
            vals.append(result)
            if result > value:
                value = result
            if value > alpha:
                alpha = value

            if alpha >= beta:
                break
        return value

    def evaluate_board_state(self, board):

        """
        Your evaluation function should look at the current state and return a score for it.
        As an example, the random agent provided works as follows:
            If the opponent has won this game, return -1.
            If we have won the game, return 1.

        If neither of the players has won, return a random number.
        These are the variables and functions for board objects
         which may be helpful when creating your Agent.
        Look into board.py for more information/descriptions of each,
         or to look for any other definitions which may help you.

        Board Variables:
            board.width
            board.height
            board.last_move
            board.num_to_connect
            board.winning_zones
            board.score_array
            board.current_player_score

        Board Functions:
            get_cell_value(row, col)
            try_move(col)
            valid_move(row, col)
            valid_moves()
            terminal(self)
            legal_moves()
            next_state(turn)
            winner()
        """
        npboard = np.array(board.board)
        return (
            (
                vertical_threat(npboard) + horizontal_threat(npboard)
                + diagonal_threat(npboard))**2
            + central_heuristic(board)/10
        )


def vertical_threat(board_array):
    """Function to determine how many vertical threats exist
    returns score for how many more threats player1 has over player2
    """
    h, w = board_array.shape
    score = 0

    mask = np.array([0, 1, 1, 1])

    for c in range(w):
        for r in range(h-3):
            if (board_array[r:r+4, c] == mask).all():
                score += 1
            elif (board_array[r:r+4, c] == 2*mask).all():
                score -= 1
    return score


def horizontal_threat(board_array):
    """Function to determine how many horizontal threats exist
    returns score for how many more threats player1 has over player2
    """
    h, w = board_array.shape
    score = 0

    masks = [np.array([1,1,1,0]),
             np.array([1,1,0,1]),
             np.array([1,0,1,1]),
             np.array([0,1,1,1])]


    for c in range(w-3):
        for r in range(h):
            board_slice = board_array[r, c:c+4]
            for mask in masks:
                if (board_slice == mask).all():
                    score += 1
                elif (board_slice == 2*mask).all():
                    score -= 1
    return score


def diagonal_threat(board_array):
    """Function to determine how many diagonal threats exist
    returns score for how many more threats player1 has over player2
    """
    h, w = board_array.shape
    score = 0

    masks = [np.array([1,1,1,0]),
             np.array([1,1,0,1]),
             np.array([1,0,1,1]),
             np.array([0,1,1,1])]

    for c in range(w-3):
        for r in range(h-3):
            board_slices = [board_array[r:r+4, c:c+4].diagonal(),
                            np.fliplr(board_array[r:r+4, c:c+4]).diagonal()]
            for board_slice in board_slices:
                for mask in masks:
                    if (board_slice == mask).all():
                        score += 1
                    elif (board_slice == 2*mask).all():
                        score -= 1
    return score


def central_heuristic(board):
    """Simple heuristic to favour boards that have more central tokens
    Returns the sum of the tokens multiplied by their distance from edge of board
    outer column = 0, middle column = 3 for a 7 column board
    """
    middle_score = 0
    middle_col = round((board.width+1)/2)-1
    for row in board.board:
        for col in range(board.width):
            score = middle_col-abs(middle_col-col)
            if row[col] == 1:
                middle_score += score
            elif row[col] == 2:
                middle_score -= score
    return middle_score
