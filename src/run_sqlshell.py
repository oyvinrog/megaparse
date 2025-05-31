import sys
import sqlshell

if __name__ == "__main__":
    db_file = sys.argv[1]
    sqlshell.start(db_file) 