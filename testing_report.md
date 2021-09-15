
1. Submission Tests
tests are in submission_test dir
tests are run with Postman

# Test Cases
2. Part 1: Single Node Message Queue

$ python3 test_part1.py
$ chmod 755 ./shutall.sh    
$ ./shutall.sh

This test suite uses assertions.
Test cases include
3. successful creation of topic
3. successful getting list of topics
3. successful pushing 2 messages to a topic
3. prevent pushing to nonexistent topic
3. successful dequeueing of message in order
3. prevent dequeueing of empty queue
3. prevent dequeueing of nonexistent topic

run ./shutall.sh after, to make sure all processes and ports are killed.

2. Part 2: Leader Election Algo

$ python3 test_part2.py
$ chmod 755 ./shutall.sh    
$ ./shutall.sh

This test suite uses assertions.
Test cases include
3. successful creation of multiple nodes
3. successful election of one leader
3. kill one leader
3. successful reelection of one leader

run ./shutall.sh after, to make sure all processes and ports are killed.

2. Part 3: Distributed Replication Model

refer to technical report for Postman testing instructions

2. Fault Tolerance

1. Provided Tests
All tests in message_queue_test.py, election_test.py passed.
In replication_test, the tests test_is_topic_shared, test_is_message_shared fail at last line, assering Leader2 != None
This seems to point to no new leader being elected. However election_test.py passes, while testing with Submission Tests both show that new leaders are being elected.

1. Notes on Errors
Added stdout printing in test_utils.py, outputs "stdout_capture<inbdex>.txt"
Used raise Exception() to examine variables, errors at differnet points