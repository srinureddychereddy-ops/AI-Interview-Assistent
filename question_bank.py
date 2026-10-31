"""
question_bank.py — Comprehensive Question Bank for Interview.ai Coding Round
Covers 10 domains across Easy, Medium, and Hard difficulty levels.
Each question includes:
- Metadata: id, title, domain, difficulty, role, tags
- Problem statement: description, examples, constraints
- Code template: starter_code, function_name, comparator
- Test cases: visible test cases (for Run Code) and hidden test cases (for Submit Solution)
- Complexity analysis: expected time_complexity, space_complexity
"""

import copy
import random
from typing import List, Dict, Any, Optional

# Supported domains
DOMAINS = [
    "Software Engineering",
    "Backend Development",
    "Frontend Development",
    "Full Stack Development",
    "Data Science",
    "AI / Machine Learning",
    "DevOps",
    "Data Engineering",
    "Mobile Development",
    "Cybersecurity"
]

QUESTION_BANK: List[Dict[str, Any]] = [
    # =========================================================================
    # 1. SOFTWARE ENGINEERING
    # =========================================================================
    {
        "id": "se-two-sum",
        "title": "Two Sum",
        "domain": "Software Engineering",
        "difficulty": "Easy",
        "tags": ["Array", "Hash Table"],
        "time_complexity": "O(n)",
        "space_complexity": "O(n)",
        "function_name": "two_sum",
        "comparator": "unordered_list",
        "description": "Given an array of integers <code>nums</code> and an integer <code>target</code>, return indices of the two numbers such that they add up to <code>target</code>.<br><br>You may assume that each input would have exactly one solution, and you may not use the same element twice. You can return the answer in any order.",
        "examples": [
            {"input": "nums = [2,7,11,15], target = 9", "output": "[0,1]", "explanation": "nums[0] + nums[1] == 9, so we return [0, 1]."},
            {"input": "nums = [3,2,4], target = 6", "output": "[1,2]", "explanation": "nums[1] + nums[2] == 6, so we return [1, 2]."}
        ],
        "constraints": ["2 <= nums.length <= 10^4", "-10^9 <= nums[i] <= 10^9", "Exactly one valid answer exists."],
        "starter_code": "def two_sum(nums, target):\n    # Write your solution here\n    pass\n",
        "test_cases": [
            {"id": 1, "input": {"nums": [2, 7, 11, 15], "target": 9}, "expected": [0, 1]},
            {"id": 2, "input": {"nums": [3, 2, 4], "target": 6}, "expected": [1, 2]}
        ],
        "hidden_test_cases": [
            {"id": 3, "input": {"nums": [3, 3], "target": 6}, "expected": [0, 1]},
            {"id": 4, "input": {"nums": [-1, -2, -3, -4, -5], "target": -8}, "expected": [2, 4]},
            {"id": 5, "input": {"nums": [0, 4, 3, 0], "target": 0}, "expected": [0, 3]}
        ]
    },
    {
        "id": "se-valid-palindrome",
        "title": "Valid Palindrome",
        "domain": "Software Engineering",
        "difficulty": "Easy",
        "tags": ["String", "Two Pointers"],
        "time_complexity": "O(n)",
        "space_complexity": "O(1)",
        "function_name": "is_palindrome",
        "comparator": "exact",
        "description": "A phrase is a palindrome if, after converting all uppercase letters into lowercase letters and removing all non-alphanumeric characters, it reads the same forward and backward.<br><br>Given a string <code>s</code>, return <code>true</code> if it is a palindrome, or <code>false</code> otherwise.",
        "examples": [
            {"input": 's = "A man, a plan, a canal: Panama"', "output": "true", "explanation": '"amanaplanacanalpanama" is a palindrome.'},
            {"input": 's = "race a car"', "output": "false", "explanation": '"raceacar" is not a palindrome.'}
        ],
        "constraints": ["1 <= s.length <= 2 * 10^5", "s consists only of printable ASCII characters."],
        "starter_code": "def is_palindrome(s):\n    # Write your solution here\n    pass\n",
        "test_cases": [
            {"id": 1, "input": {"s": "A man, a plan, a canal: Panama"}, "expected": True},
            {"id": 2, "input": {"s": "race a car"}, "expected": False}
        ],
        "hidden_test_cases": [
            {"id": 3, "input": {"s": " "}, "expected": True},
            {"id": 4, "input": {"s": "0P"}, "expected": False},
            {"id": 5, "input": {"s": "Was it a car or a cat I saw?"}, "expected": True}
        ]
    },
    {
        "id": "se-contains-duplicate",
        "title": "Contains Duplicate",
        "domain": "Software Engineering",
        "difficulty": "Easy",
        "tags": ["Array", "Hash Table"],
        "time_complexity": "O(n)",
        "space_complexity": "O(n)",
        "function_name": "contains_duplicate",
        "comparator": "exact",
        "description": "Given an integer array <code>nums</code>, return <code>true</code> if any value appears at least twice in the array, and return <code>false</code> if every element is distinct.",
        "examples": [
            {"input": "nums = [1,2,3,1]", "output": "true", "explanation": "1 appears twice."},
            {"input": "nums = [1,2,3,4]", "output": "false", "explanation": "All elements are distinct."}
        ],
        "constraints": ["1 <= nums.length <= 10^5", "-10^9 <= nums[i] <= 10^9"],
        "starter_code": "def contains_duplicate(nums):\n    # Write your solution here\n    pass\n",
        "test_cases": [
            {"id": 1, "input": {"nums": [1, 2, 3, 1]}, "expected": True},
            {"id": 2, "input": {"nums": [1, 2, 3, 4]}, "expected": False}
        ],
        "hidden_test_cases": [
            {"id": 3, "input": {"nums": [1, 1, 1, 3, 3, 4, 3, 2, 4, 2]}, "expected": True},
            {"id": 4, "input": {"nums": [42]}, "expected": False}
        ]
    },
    {
        "id": "se-reverse-string",
        "title": "Reverse String",
        "domain": "Software Engineering",
        "difficulty": "Easy",
        "tags": ["String", "Two Pointers"],
        "time_complexity": "O(n)",
        "space_complexity": "O(n)",
        "function_name": "reverse_string",
        "comparator": "exact",
        "description": "Write a function that reverses a given string <code>s</code> and returns the reversed string.",
        "examples": [
            {"input": 's = "hello"', "output": '"olleh"', "explanation": "The characters in reverse order."},
            {"input": 's = "Hannah"', "output": '"hannaH"', "explanation": "Case is preserved."}
        ],
        "constraints": ["1 <= s.length <= 10^5"],
        "starter_code": "def reverse_string(s):\n    # Write your solution here\n    pass\n",
        "test_cases": [
            {"id": 1, "input": {"s": "hello"}, "expected": "olleh"},
            {"id": 2, "input": {"s": "Hannah"}, "expected": "hannaH"}
        ],
        "hidden_test_cases": [
            {"id": 3, "input": {"s": "a"}, "expected": "a"},
            {"id": 4, "input": {"s": "racecar"}, "expected": "racecar"}
        ]
    },
    {
        "id": "se-group-anagrams",
        "title": "Group Anagrams",
        "domain": "Software Engineering",
        "difficulty": "Medium",
        "tags": ["Array", "Hash Table", "String"],
        "time_complexity": "O(n * k log k)",
        "space_complexity": "O(n * k)",
        "function_name": "group_anagrams",
        "comparator": "grouped_lists",
        "description": "Given an array of strings <code>strs</code>, group the anagrams together. You can return the answer in any order.<br><br>An Anagram is a word or phrase formed by rearranging the letters of a different word or phrase.",
        "examples": [
            {"input": 'strs = ["eat","tea","tan","ate","nat","bat"]', "output": '[["bat"],["nat","tan"],["ate","eat","tea"]]'}
        ],
        "constraints": ["1 <= strs.length <= 10^4", "0 <= strs[i].length <= 100"],
        "starter_code": "def group_anagrams(strs):\n    # Write your solution here\n    pass\n",
        "test_cases": [
            {"id": 1, "input": {"strs": ["eat", "tea", "tan", "ate", "nat", "bat"]}, "expected": [["bat"], ["nat", "tan"], ["ate", "eat", "tea"]]},
            {"id": 2, "input": {"strs": [""]}, "expected": [[""]]}
        ],
        "hidden_test_cases": [
            {"id": 3, "input": {"strs": ["a"]}, "expected": [["a"]]},
            {"id": 4, "input": {"strs": ["cab", "tin", "pew", "duh", "may", "ill", "buy", "bar", "max", "doc"]}, "expected": [["cab"], ["tin"], ["pew"], ["duh"], ["may"], ["ill"], ["buy"], ["bar"], ["max"], ["doc"]]}
        ]
    },
    {
        "id": "se-longest-substring",
        "title": "Longest Substring Without Repeating Characters",
        "domain": "Software Engineering",
        "difficulty": "Medium",
        "tags": ["Hash Table", "String", "Sliding Window"],
        "time_complexity": "O(n)",
        "space_complexity": "O(min(m, n))",
        "function_name": "length_of_longest_substring",
        "comparator": "exact",
        "description": "Given a string <code>s</code>, find the length of the longest substring without duplicate characters.",
        "examples": [
            {"input": 's = "abcabcbb"', "output": "3", "explanation": 'The answer is "abc", with the length of 3.'},
            {"input": 's = "bbbbb"', "output": "1", "explanation": 'The answer is "b", with the length of 1.'}
        ],
        "constraints": ["0 <= s.length <= 5 * 10^4"],
        "starter_code": "def length_of_longest_substring(s):\n    # Write your solution here\n    pass\n",
        "test_cases": [
            {"id": 1, "input": {"s": "abcabcbb"}, "expected": 3},
            {"id": 2, "input": {"s": "bbbbb"}, "expected": 1}
        ],
        "hidden_test_cases": [
            {"id": 3, "input": {"s": "pwwkew"}, "expected": 3},
            {"id": 4, "input": {"s": ""}, "expected": 0},
            {"id": 5, "input": {"s": " "}, "expected": 1}
        ]
    },
    {
        "id": "se-merge-intervals",
        "title": "Merge Intervals",
        "domain": "Software Engineering",
        "difficulty": "Medium",
        "tags": ["Array", "Sorting"],
        "time_complexity": "O(n log n)",
        "space_complexity": "O(n)",
        "function_name": "merge_intervals",
        "comparator": "exact",
        "description": "Given an array of <code>intervals</code> where <code>intervals[i] = [start_i, end_i]</code>, merge all overlapping intervals, and return an array of the non-overlapping intervals that cover all the intervals in the input.",
        "examples": [
            {"input": "intervals = [[1,3],[2,6],[8,10],[15,18]]", "output": "[[1,6],[8,10],[15,18]]", "explanation": "Intervals [1,3] and [2,6] overlap, merging into [1,6]."},
            {"input": "intervals = [[1,4],[4,5]]", "output": "[[1,5]]", "explanation": "Intervals [1,4] and [4,5] are considered overlapping."}
        ],
        "constraints": ["1 <= intervals.length <= 10^4", "intervals[i].length == 2"],
        "starter_code": "def merge_intervals(intervals):\n    # Write your solution here\n    pass\n",
        "test_cases": [
            {"id": 1, "input": {"intervals": [[1, 3], [2, 6], [8, 10], [15, 18]]}, "expected": [[1, 6], [8, 10], [15, 18]]},
            {"id": 2, "input": {"intervals": [[1, 4], [4, 5]]}, "expected": [[1, 5]]}
        ],
        "hidden_test_cases": [
            {"id": 3, "input": {"intervals": [[1, 4], [0, 4]]}, "expected": [[0, 4]]},
            {"id": 4, "input": {"intervals": [[1, 4], [2, 3]]}, "expected": [[1, 4]]}
        ]
    },
    {
        "id": "se-product-except-self",
        "title": "Product of Array Except Self",
        "domain": "Software Engineering",
        "difficulty": "Medium",
        "tags": ["Array", "Prefix Sum"],
        "time_complexity": "O(n)",
        "space_complexity": "O(1)",
        "function_name": "product_except_self",
        "comparator": "exact",
        "description": "Given an integer array <code>nums</code>, return an array <code>answer</code> such that <code>answer[i]</code> is equal to the product of all the elements of <code>nums</code> except <code>nums[i]</code>.<br><br>You must write an algorithm that runs in <code>O(n)</code> time and without using the division operation.",
        "examples": [
            {"input": "nums = [1,2,3,4]", "output": "[24,12,8,6]"},
            {"input": "nums = [-1,1,0,-3,3]", "output": "[0,0,9,0,0]"}
        ],
        "constraints": ["2 <= nums.length <= 10^5", "-30 <= nums[i] <= 30"],
        "starter_code": "def product_except_self(nums):\n    # Write your solution here\n    pass\n",
        "test_cases": [
            {"id": 1, "input": {"nums": [1, 2, 3, 4]}, "expected": [24, 12, 8, 6]},
            {"id": 2, "input": {"nums": [-1, 1, 0, -3, 3]}, "expected": [0, 0, 9, 0, 0]}
        ],
        "hidden_test_cases": [
            {"id": 3, "input": {"nums": [0, 0]}, "expected": [0, 0]},
            {"id": 4, "input": {"nums": [5, 2]}, "expected": [2, 5]}
        ]
    },
    {
        "id": "se-lru-cache",
        "title": "LRU Cache Simulator",
        "domain": "Software Engineering",
        "difficulty": "Hard",
        "tags": ["Design", "Hash Table", "Linked List"],
        "time_complexity": "O(1) per operation",
        "space_complexity": "O(capacity)",
        "function_name": "simulate_lru_cache",
        "comparator": "exact",
        "description": "Design a data structure that follows the constraints of a Least Recently Used (LRU) cache.<br><br>Implement a function <code>simulate_lru_cache(capacity, operations)</code> where <code>operations</code> is a list of tuples <code>('put', key, val)</code> or <code>('get', key)</code>. Return a list of results corresponding to each <code>get</code> operation (return -1 if key not found).",
        "examples": [
            {"input": "capacity = 2, operations = [('put', 1, 1), ('put', 2, 2), ('get', 1), ('put', 3, 3), ('get', 2)]", "output": "[1, -1]", "explanation": "Key 2 was evicted when key 3 was added."}
        ],
        "constraints": ["1 <= capacity <= 3000", "0 <= operations.length <= 10^4"],
        "starter_code": "def simulate_lru_cache(capacity, operations):\n    # Write your solution here\n    pass\n",
        "test_cases": [
            {"id": 1, "input": {"capacity": 2, "operations": [["put", 1, 1], ["put", 2, 2], ["get", 1], ["put", 3, 3], ["get", 2]]}, "expected": [1, -1]},
            {"id": 2, "input": {"capacity": 1, "operations": [["put", 10, 100], ["get", 10], ["get", 20]]}, "expected": [100, -1]}
        ],
        "hidden_test_cases": [
            {"id": 3, "input": {"capacity": 2, "operations": [["get", 2], ["put", 2, 6], ["get", 1], ["put", 1, 5], ["put", 1, 2], ["get", 1], ["get", 2]]}, "expected": [-1, -1, 2, 6]}
        ]
    },

    # =========================================================================
    # 2. BACKEND DEVELOPMENT
    # =========================================================================
    {
        "id": "be-validate-api-request",
        "title": "Validate API Request",
        "domain": "Backend Development",
        "difficulty": "Easy",
        "tags": ["API", "Validation", "Hash Table"],
        "time_complexity": "O(k)",
        "space_complexity": "O(k)",
        "function_name": "validate_api_request",
        "comparator": "exact",
        "description": "Given a request body dictionary <code>payload</code> and a list of required field names <code>required_fields</code>, return <code>true</code> if all required fields are present with non-empty values (non-None, non-empty string), otherwise return <code>false</code>.",
        "examples": [
            {"input": 'payload = {"user_id": 101, "email": "a@b.com"}, required_fields = ["user_id", "email"]', "output": "true"},
            {"input": 'payload = {"user_id": 101, "email": ""}, required_fields = ["user_id", "email"]', "output": "false"}
        ],
        "constraints": ["1 <= len(required_fields) <= 100"],
        "starter_code": "def validate_api_request(payload, required_fields):\n    # Write your solution here\n    pass\n",
        "test_cases": [
            {"id": 1, "input": {"payload": {"user_id": 101, "email": "dev@test.com"}, "required_fields": ["user_id", "email"]}, "expected": True},
            {"id": 2, "input": {"payload": {"user_id": 101, "email": ""}, "required_fields": ["user_id", "email"]}, "expected": False}
        ],
        "hidden_test_cases": [
            {"id": 3, "input": {"payload": {"token": None}, "required_fields": ["token"]}, "expected": False},
            {"id": 4, "input": {"payload": {"a": 1, "b": 2, "c": 3}, "required_fields": ["a", "c"]}, "expected": True}
        ]
    },
    {
        "id": "be-parse-query-params",
        "title": "Parse Query Parameters",
        "domain": "Backend Development",
        "difficulty": "Easy",
        "tags": ["String", "Parsing", "Hash Table"],
        "time_complexity": "O(n)",
        "space_complexity": "O(n)",
        "function_name": "parse_query_params",
        "comparator": "exact",
        "description": "Given a URL query string <code>query</code> (without the leading '?'), parse it into a key-value dictionary. If a key appears multiple times, its value should be a list of string values in order.",
        "examples": [
            {"input": 'query = "page=1&limit=20"', "output": '{"page": "1", "limit": "20"}'},
            {"input": 'query = "tag=python&tag=backend"', "output": '{"tag": ["python", "backend"]}'}
        ],
        "constraints": ["0 <= query.length <= 1000"],
        "starter_code": "def parse_query_params(query):\n    # Write your solution here\n    pass\n",
        "test_cases": [
            {"id": 1, "input": {"query": "page=1&limit=20"}, "expected": {"page": "1", "limit": "20"}},
            {"id": 2, "input": {"query": "tag=python&tag=backend"}, "expected": {"tag": ["python", "backend"]}}
        ],
        "hidden_test_cases": [
            {"id": 3, "input": {"query": ""}, "expected": {}},
            {"id": 4, "input": {"query": "search=algo&mode="}, "expected": {"search": "algo", "mode": ""}}
        ]
    },
    {
        "id": "be-rate-limiter",
        "title": "Sliding Window Rate Limiter",
        "domain": "Backend Development",
        "difficulty": "Medium",
        "tags": ["System Design", "Queue", "Algorithms"],
        "time_complexity": "O(n)",
        "space_complexity": "O(n)",
        "function_name": "is_request_allowed",
        "comparator": "exact",
        "description": "Implement a sliding window rate limiter function <code>is_request_allowed(timestamps, limit, window_size)</code>. Given a list of ascending request timestamps (in seconds), return a list of booleans indicating whether each request is permitted under the rate limit (maximum <code>limit</code> requests within any <code>window_size</code> second sliding window).",
        "examples": [
            {"input": "timestamps = [1, 2, 3, 5], limit = 3, window_size = 5", "output": "[true, true, true, false]"}
        ],
        "constraints": ["1 <= timestamps.length <= 10^4", "timestamps is sorted non-decreasingly."],
        "starter_code": "def is_request_allowed(timestamps, limit, window_size):\n    # Write your solution here\n    pass\n",
        "test_cases": [
            {"id": 1, "input": {"timestamps": [1, 2, 3, 5], "limit": 3, "window_size": 5}, "expected": [True, True, True, False]},
            {"id": 2, "input": {"timestamps": [1, 10, 20], "limit": 2, "window_size": 5}, "expected": [True, True, True]}
        ],
        "hidden_test_cases": [
            {"id": 3, "input": {"timestamps": [1, 1, 1, 1], "limit": 2, "window_size": 10}, "expected": [True, True, False, False]},
            {"id": 4, "input": {"timestamps": [1, 2, 3, 6, 7], "limit": 2, "window_size": 3}, "expected": [True, True, False, True, True]}
        ]
    },
    {
        "id": "be-log-aggregation",
        "title": "API Request Deduplication",
        "domain": "Backend Development",
        "difficulty": "Medium",
        "tags": ["Hash Table", "Deduplication", "Backend"],
        "time_complexity": "O(n)",
        "space_complexity": "O(n)",
        "function_name": "deduplicate_requests",
        "comparator": "exact",
        "description": "Given a list of request log objects where each object is a dictionary with <code>request_id</code>, <code>idempotency_key</code>, and <code>payload</code>, return a list of unique <code>request_id</code>s for requests processed, ignoring subsequent requests that share an existing <code>idempotency_key</code>.",
        "examples": [
            {"input": 'requests = [{"request_id": 1, "idempotency_key": "k1"}, {"request_id": 2, "idempotency_key": "k1"}, {"request_id": 3, "idempotency_key": "k2"}]', "output": "[1, 3]"}
        ],
        "constraints": ["1 <= requests.length <= 10^4"],
        "starter_code": "def deduplicate_requests(requests):\n    # Write your solution here\n    pass\n",
        "test_cases": [
            {"id": 1, "input": {"requests": [{"request_id": 1, "idempotency_key": "k1"}, {"request_id": 2, "idempotency_key": "k1"}, {"request_id": 3, "idempotency_key": "k2"}]}, "expected": [1, 3]},
            {"id": 2, "input": {"requests": [{"request_id": 10, "idempotency_key": "a"}]}, "expected": [10]}
        ],
        "hidden_test_cases": [
            {"id": 3, "input": {"requests": [{"request_id": 1, "idempotency_key": "x"}, {"request_id": 2, "idempotency_key": "y"}, {"request_id": 3, "idempotency_key": "z"}]}, "expected": [1, 2, 3]}
        ]
    },
    {
        "id": "be-task-scheduler",
        "title": "Task Scheduler with Dependencies",
        "domain": "Backend Development",
        "difficulty": "Hard",
        "tags": ["Graph", "Topological Sort", "Algorithms"],
        "time_complexity": "O(V + E)",
        "space_complexity": "O(V + E)",
        "function_name": "find_execution_order",
        "comparator": "valid_topological_sort",
        "description": "You are given <code>num_tasks</code> labeled from <code>0</code> to <code>num_tasks - 1</code> and a list of dependency pairs <code>[task, prereq]</code> indicating that <code>prereq</code> must be completed before <code>task</code> can run.<br><br>Return a valid order in which all tasks should be executed. If it is impossible due to a cyclic dependency, return an empty list <code>[]</code>.",
        "examples": [
            {"input": "num_tasks = 2, dependencies = [[1,0]]", "output": "[0,1]"},
            {"input": "num_tasks = 2, dependencies = [[1,0],[0,1]]", "output": "[]", "explanation": "Cycle detected."}
        ],
        "constraints": ["1 <= num_tasks <= 2000", "0 <= dependencies.length <= 5000"],
        "starter_code": "def find_execution_order(num_tasks, dependencies):\n    # Write your solution here\n    pass\n",
        "test_cases": [
            {"id": 1, "input": {"num_tasks": 2, "dependencies": [[1, 0]]}, "expected": [0, 1]},
            {"id": 2, "input": {"num_tasks": 2, "dependencies": [[1, 0], [0, 1]]}, "expected": []}
        ],
        "hidden_test_cases": [
            {"id": 3, "input": {"num_tasks": 4, "dependencies": [[1, 0], [2, 0], [3, 1], [3, 2]]}, "expected": [0, 1, 2, 3]},
            {"id": 4, "input": {"num_tasks": 1, "dependencies": []}, "expected": [0]}
        ]
    },

    # =========================================================================
    # 3. FRONTEND DEVELOPMENT
    # =========================================================================
    {
        "id": "fe-string-formatter",
        "title": "Format Template String",
        "domain": "Frontend Development",
        "difficulty": "Easy",
        "tags": ["String", "Formatting", "Templating"],
        "time_complexity": "O(n)",
        "space_complexity": "O(n)",
        "function_name": "format_template",
        "comparator": "exact",
        "description": "Write a template interpolation function <code>format_template(template, context)</code> that replaces placeholders like <code>{key}</code> with values from the <code>context</code> dictionary. If a key is missing from context, leave the placeholder unchanged.",
        "examples": [
            {"input": 'template = "Hello {name}, welcome to {app}!", context = {"name": "Alice", "app": "Interview.ai"}', "output": '"Hello Alice, welcome to Interview.ai!"'}
        ],
        "constraints": ["0 <= len(template) <= 1000"],
        "starter_code": "def format_template(template, context):\n    # Write your solution here\n    pass\n",
        "test_cases": [
            {"id": 1, "input": {"template": "Hello {name}, welcome to {app}!", "context": {"name": "Alice", "app": "Interview.ai"}}, "expected": "Hello Alice, welcome to Interview.ai!"},
            {"id": 2, "input": {"template": "Value: {val}, Missing: {missing}", "context": {"val": 42}}, "expected": "Value: 42, Missing: {missing}"}
        ],
        "hidden_test_cases": [
            {"id": 3, "input": {"template": "No tokens here", "context": {}}, "expected": "No tokens here"}
        ]
    },
    {
        "id": "fe-flatten-nested-object",
        "title": "Flatten Nested Object",
        "domain": "Frontend Development",
        "difficulty": "Medium",
        "tags": ["Recursion", "Data Structures", "JSON"],
        "time_complexity": "O(n)",
        "space_complexity": "O(n)",
        "function_name": "flatten_object",
        "comparator": "exact",
        "description": "Given a nested dictionary <code>obj</code>, flatten it into a single-level dictionary where keys are dot-separated paths representing the nested hierarchy.",
        "examples": [
            {"input": 'obj = {"user": {"name": "John", "address": {"city": "Boston"}}}', "output": '{"user.name": "John", "user.address.city": "Boston"}'}
        ],
        "constraints": ["Dictionary depth <= 10"],
        "starter_code": "def flatten_object(obj):\n    # Write your solution here\n    pass\n",
        "test_cases": [
            {"id": 1, "input": {"obj": {"user": {"name": "John", "address": {"city": "Boston"}}}}, "expected": {"user.name": "John", "user.address.city": "Boston"}},
            {"id": 2, "input": {"obj": {"a": 1, "b": 2}}, "expected": {"a": 1, "b": 2}}
        ],
        "hidden_test_cases": [
            {"id": 3, "input": {"obj": {"x": {"y": {"z": 100}}}}, "expected": {"x.y.z": 100}},
            {"id": 4, "input": {"obj": {}}, "expected": {}}
        ]
    },
    {
        "id": "fe-deep-clone",
        "title": "Deep Clone Object",
        "domain": "Frontend Development",
        "difficulty": "Medium",
        "tags": ["Recursion", "Objects"],
        "time_complexity": "O(n)",
        "space_complexity": "O(n)",
        "function_name": "deep_clone",
        "comparator": "exact",
        "description": "Implement a deep clone algorithm <code>deep_clone(data)</code> that produces an independent deep copy of nested dictionaries and lists without using Python's <code>copy.deepcopy</code> module.",
        "examples": [
            {"input": 'data = {"a": [1, 2, {"b": 3}]}', "output": '{"a": [1, 2, {"b": 3}]}'}
        ],
        "constraints": ["No circular references in test data."],
        "starter_code": "def deep_clone(data):\n    # Write your solution here\n    pass\n",
        "test_cases": [
            {"id": 1, "input": {"data": {"a": [1, 2, {"b": 3}]}}, "expected": {"a": [1, 2, {"b": 3}]}},
            {"id": 2, "input": {"data": [1, [2, [3]]]}, "expected": [1, [2, [3]]]}
        ],
        "hidden_test_cases": [
            {"id": 3, "input": {"data": "primitive"}, "expected": "primitive"},
            {"id": 4, "input": {"data": 12345}, "expected": 12345}
        ]
    },
    {
        "id": "fe-virtualized-list-logic",
        "title": "Virtualized Window Calculator",
        "domain": "Frontend Development",
        "difficulty": "Hard",
        "tags": ["Algorithms", "Math", "Performance"],
        "time_complexity": "O(1)",
        "space_complexity": "O(1)",
        "function_name": "calculate_visible_range",
        "comparator": "exact",
        "description": "Given a virtualized list container with <code>total_items</code>, <code>item_height</code>, <code>container_height</code>, and current <code>scroll_top</code>, calculate the range of visible item indices <code>[start_idx, end_idx]</code> inclusive with an optional buffer of <code>overscan</code> items.",
        "examples": [
            {"input": "total_items = 100, item_height = 50, container_height = 200, scroll_top = 100, overscan = 1", "output": "[1, 6]"}
        ],
        "constraints": ["total_items >= 0", "item_height > 0", "container_height > 0"],
        "starter_code": "def calculate_visible_range(total_items, item_height, container_height, scroll_top, overscan=1):\n    # Write your solution here\n    pass\n",
        "test_cases": [
            {"id": 1, "input": {"total_items": 100, "item_height": 50, "container_height": 200, "scroll_top": 100, "overscan": 1}, "expected": [1, 6]},
            {"id": 2, "input": {"total_items": 5, "item_height": 40, "container_height": 200, "scroll_top": 0, "overscan": 0}, "expected": [0, 4]}
        ],
        "hidden_test_cases": [
            {"id": 3, "input": {"total_items": 0, "item_height": 50, "container_height": 200, "scroll_top": 0, "overscan": 2}, "expected": [0, 0]}
        ]
    },

    # =========================================================================
    # 4. FULL STACK DEVELOPMENT
    # =========================================================================
    {
        "id": "fs-pagination-helper",
        "title": "Pagination Helper",
        "domain": "Full Stack Development",
        "difficulty": "Easy",
        "tags": ["Pagination", "Algorithms"],
        "time_complexity": "O(1)",
        "space_complexity": "O(1)",
        "function_name": "paginate_items",
        "comparator": "exact",
        "description": "Write a pagination helper function <code>paginate_items(items, page, page_size)</code> (1-indexed) that returns a slice of the items for the specified page along with total page count: <code>{'items': [...], 'page': page, 'total_pages': total_pages, 'total_items': len(items)}</code>.",
        "examples": [
            {"input": "items = [1,2,3,4,5,6,7], page = 2, page_size = 3", "output": "{'items': [4,5,6], 'page': 2, 'total_pages': 3, 'total_items': 7}"}
        ],
        "constraints": ["page >= 1", "page_size >= 1"],
        "starter_code": "def paginate_items(items, page, page_size):\n    # Write your solution here\n    pass\n",
        "test_cases": [
            {"id": 1, "input": {"items": [1, 2, 3, 4, 5, 6, 7], "page": 2, "page_size": 3}, "expected": {"items": [4, 5, 6], "page": 2, "total_pages": 3, "total_items": 7}},
            {"id": 2, "input": {"items": [1, 2], "page": 1, "page_size": 5}, "expected": {"items": [1, 2], "page": 1, "total_pages": 1, "total_items": 2}}
        ],
        "hidden_test_cases": [
            {"id": 3, "input": {"items": [], "page": 1, "page_size": 10}, "expected": {"items": [], "page": 1, "total_pages": 0, "total_items": 0}},
            {"id": 4, "input": {"items": [10, 20, 30], "page": 5, "page_size": 2}, "expected": {"items": [], "page": 5, "total_pages": 2, "total_items": 3}}
        ]
    },
    {
        "id": "fs-shopping-cart-logic",
        "title": "Shopping Cart Calculator",
        "domain": "Full Stack Development",
        "difficulty": "Medium",
        "tags": ["Full Stack", "Business Logic"],
        "time_complexity": "O(n)",
        "space_complexity": "O(1)",
        "function_name": "calculate_cart_total",
        "comparator": "exact",
        "description": "Calculate the cart total given a list of item dictionaries with <code>price</code>, <code>quantity</code>, and optional <code>discount_percent</code> (0-100), plus a global tax rate (e.g. 0.08 for 8%). Return the rounded total to 2 decimal places.",
        "examples": [
            {"input": "items = [{'price': 100, 'quantity': 1, 'discount_percent': 10}], tax_rate = 0.05", "output": "94.5"}
        ],
        "constraints": ["price >= 0", "quantity >= 0"],
        "starter_code": "def calculate_cart_total(items, tax_rate):\n    # Write your solution here\n    pass\n",
        "test_cases": [
            {"id": 1, "input": {"items": [{"price": 100, "quantity": 1, "discount_percent": 10}], "tax_rate": 0.05}, "expected": 94.5},
            {"id": 2, "input": {"items": [{"price": 50, "quantity": 2}], "tax_rate": 0.10}, "expected": 110.0}
        ],
        "hidden_test_cases": [
            {"id": 3, "input": {"items": [], "tax_rate": 0.08}, "expected": 0.0}
        ]
    },
    {
        "id": "fs-job-queue",
        "title": "Priority Job Queue Processor",
        "domain": "Full Stack Development",
        "difficulty": "Hard",
        "tags": ["Heap", "Queue", "System Design"],
        "time_complexity": "O(n log n)",
        "space_complexity": "O(n)",
        "function_name": "process_job_queue",
        "comparator": "exact",
        "description": "Given a list of job requests with <code>id</code>, <code>priority</code> (higher number = higher priority), and <code>timestamp</code>, return the order of job <code>id</code>s executed. Ties in priority should be broken by earliest timestamp (FIFO).",
        "examples": [
            {"input": "jobs = [{'id': 'A', 'priority': 1, 'timestamp': 10}, {'id': 'B', 'priority': 3, 'timestamp': 5}, {'id': 'C', 'priority': 3, 'timestamp': 2}]", "output": "['C', 'B', 'A']"}
        ],
        "constraints": ["1 <= len(jobs) <= 10^4"],
        "starter_code": "def process_job_queue(jobs):\n    # Write your solution here\n    pass\n",
        "test_cases": [
            {"id": 1, "input": {"jobs": [{"id": "A", "priority": 1, "timestamp": 10}, {"id": "B", "priority": 3, "timestamp": 5}, {"id": "C", "priority": 3, "timestamp": 2}]}, "expected": ["C", "B", "A"]},
            {"id": 2, "input": {"jobs": [{"id": "X", "priority": 2, "timestamp": 1}, {"id": "Y", "priority": 2, "timestamp": 2}]}, "expected": ["X", "Y"]}
        ],
        "hidden_test_cases": [
            {"id": 3, "input": {"jobs": [{"id": "1", "priority": 10, "timestamp": 100}]}, "expected": ["1"]}
        ]
    },

    # =========================================================================
    # 5. DATA SCIENCE
    # =========================================================================
    {
        "id": "ds-calculate-mean-outliers",
        "title": "Remove Outliers and Calculate Mean",
        "domain": "Data Science",
        "difficulty": "Easy",
        "tags": ["Statistics", "Data Cleaning"],
        "time_complexity": "O(n log n)",
        "space_complexity": "O(n)",
        "function_name": "trimmed_mean",
        "comparator": "exact",
        "description": "Given a list of numerical values <code>values</code> and a trim fraction <code>alpha</code> (e.g. 0.1 for 10% on each tail), compute the trimmed mean: remove the top and bottom <code>floor(len(values) * alpha)</code> elements and return the mean of the remaining elements rounded to 2 decimal places.",
        "examples": [
            {"input": "values = [1, 2, 3, 4, 100], alpha = 0.2", "output": "3.0"}
        ],
        "constraints": ["1 <= len(values) <= 10^5", "0.0 <= alpha < 0.5"],
        "starter_code": "def trimmed_mean(values, alpha):\n    # Write your solution here\n    pass\n",
        "test_cases": [
            {"id": 1, "input": {"values": [1, 2, 3, 4, 100], "alpha": 0.2}, "expected": 3.0},
            {"id": 2, "input": {"values": [10, 20, 30], "alpha": 0.0}, "expected": 20.0}
        ],
        "hidden_test_cases": [
            {"id": 3, "input": {"values": [5, 5, 5, 5], "alpha": 0.25}, "expected": 5.0}
        ]
    },
    {
        "id": "ds-moving-average",
        "title": "Moving Average Window",
        "domain": "Data Science",
        "difficulty": "Medium",
        "tags": ["Array", "Sliding Window", "Data Processing"],
        "time_complexity": "O(n)",
        "space_complexity": "O(n)",
        "function_name": "moving_average",
        "comparator": "exact",
        "description": "Given a list of numbers <code>series</code> and an integer window size <code>k</code>, return a list of moving averages for every valid window of size <code>k</code>, each rounded to 2 decimal places.",
        "examples": [
            {"input": "series = [1, 2, 3, 4, 5], k = 3", "output": "[2.0, 3.0, 4.0]"}
        ],
        "constraints": ["1 <= k <= len(series) <= 10^5"],
        "starter_code": "def moving_average(series, k):\n    # Write your solution here\n    pass\n",
        "test_cases": [
            {"id": 1, "input": {"series": [1, 2, 3, 4, 5], "k": 3}, "expected": [2.0, 3.0, 4.0]},
            {"id": 2, "input": {"series": [10, 20], "k": 1}, "expected": [10.0, 20.0]}
        ],
        "hidden_test_cases": [
            {"id": 3, "input": {"series": [4, 4, 4, 4], "k": 2}, "expected": [4.0, 4.0, 4.0]}
        ]
    },
    {
        "id": "ds-correlation",
        "title": "Pearson Correlation Coefficient",
        "domain": "Data Science",
        "difficulty": "Hard",
        "tags": ["Math", "Statistics", "Machine Learning"],
        "time_complexity": "O(n)",
        "space_complexity": "O(1)",
        "function_name": "pearson_correlation",
        "comparator": "exact",
        "description": "Calculate the Pearson correlation coefficient between two lists of numbers <code>x</code> and <code>y</code> of equal length. Return the correlation coefficient rounded to 3 decimal places. If variance of either list is zero, return 0.0.",
        "examples": [
            {"input": "x = [1, 2, 3, 4, 5], y = [2, 4, 6, 8, 10]", "output": "1.0"},
            {"input": "x = [1, 2, 3], y = [3, 2, 1]", "output": "-1.0"}
        ],
        "constraints": ["len(x) == len(y) >= 2"],
        "starter_code": "def pearson_correlation(x, y):\n    # Write your solution here\n    pass\n",
        "test_cases": [
            {"id": 1, "input": {"x": [1, 2, 3, 4, 5], "y": [2, 4, 6, 8, 10]}, "expected": 1.0},
            {"id": 2, "input": {"x": [1, 2, 3], "y": [3, 2, 1]}, "expected": -1.0}
        ],
        "hidden_test_cases": [
            {"id": 3, "input": {"x": [5, 5, 5], "y": [1, 2, 3]}, "expected": 0.0}
        ]
    },

    # =========================================================================
    # 6. AI / MACHINE LEARNING
    # =========================================================================
    {
        "id": "ai-euclidean-distance",
        "title": "Calculate Euclidean Distance & Nearest Vector",
        "domain": "AI / Machine Learning",
        "difficulty": "Easy",
        "tags": ["Vector", "Geometry", "ML"],
        "time_complexity": "O(n * d)",
        "space_complexity": "O(1)",
        "function_name": "find_nearest_vector",
        "comparator": "exact",
        "description": "Given a target vector <code>target</code> (list of floats) and a list of candidate vectors <code>candidates</code>, return the index of the candidate vector with the smallest Euclidean distance to <code>target</code>.",
        "examples": [
            {"input": "target = [0, 0], candidates = [[1, 1], [0.5, 0.5], [2, 2]]", "output": "1"}
        ],
        "constraints": ["1 <= len(candidates) <= 10^4", "All vectors have identical dimensions."],
        "starter_code": "def find_nearest_vector(target, candidates):\n    # Write your solution here\n    pass\n",
        "test_cases": [
            {"id": 1, "input": {"target": [0, 0], "candidates": [[1, 1], [0.5, 0.5], [2, 2]]}, "expected": 1},
            {"id": 2, "input": {"target": [10], "candidates": [[5], [12], [8]]}, "expected": 1}
        ],
        "hidden_test_cases": [
            {"id": 3, "input": {"target": [1, 2, 3], "candidates": [[1, 2, 3], [4, 5, 6]]}, "expected": 0}
        ]
    },
    {
        "id": "ai-cosine-similarity",
        "title": "Cosine Similarity",
        "domain": "AI / Machine Learning",
        "difficulty": "Medium",
        "tags": ["NLP", "Vector", "Linear Algebra"],
        "time_complexity": "O(d)",
        "space_complexity": "O(1)",
        "function_name": "cosine_similarity",
        "comparator": "exact",
        "description": "Given two numerical vectors <code>vec1</code> and <code>vec2</code> of equal length, return their cosine similarity rounded to 4 decimal places. If either vector has zero magnitude, return 0.0.",
        "examples": [
            {"input": "vec1 = [1, 2], vec2 = [2, 4]", "output": "1.0"},
            {"input": "vec1 = [1, 0], vec2 = [0, 1]", "output": "0.0"}
        ],
        "constraints": ["1 <= len(vec1) <= 1000"],
        "starter_code": "def cosine_similarity(vec1, vec2):\n    # Write your solution here\n    pass\n",
        "test_cases": [
            {"id": 1, "input": {"vec1": [1, 2], "vec2": [2, 4]}, "expected": 1.0},
            {"id": 2, "input": {"vec1": [1, 0], "vec2": [0, 1]}, "expected": 0.0}
        ],
        "hidden_test_cases": [
            {"id": 3, "input": {"vec1": [0, 0], "vec2": [1, 2]}, "expected": 0.0}
        ]
    },
    {
        "id": "ai-knn-prediction",
        "title": "K-Nearest Neighbors Prediction",
        "domain": "AI / Machine Learning",
        "difficulty": "Hard",
        "tags": ["Classification", "Algorithms", "ML"],
        "time_complexity": "O(n * d + n log n)",
        "space_complexity": "O(n)",
        "function_name": "knn_classify",
        "comparator": "exact",
        "description": "Implement a simple KNN classifier function <code>knn_classify(k, train_data, target_point)</code> where <code>train_data</code> is a list of tuples <code>(features, label)</code>. Return the most common label among the <code>k</code> nearest neighbors by Euclidean distance. Ties in label count should be broken by the label with the closest nearest neighbor.",
        "examples": [
            {"input": "k = 3, train_data = [([1, 1], 'A'), ([1, 2], 'A'), ([5, 5], 'B')], target_point = [1, 1.5]", "output": "'A'"}
        ],
        "constraints": ["1 <= k <= len(train_data)"],
        "starter_code": "def knn_classify(k, train_data, target_point):\n    # Write your solution here\n    pass\n",
        "test_cases": [
            {"id": 1, "input": {"k": 3, "train_data": [[[1, 1], "A"], [[1, 2], "A"], [[5, 5], "B"]], "target_point": [1, 1.5]}, "expected": "A"},
            {"id": 2, "input": {"k": 1, "train_data": [[[0, 0], "Red"], [[10, 10], "Blue"]], "target_point": [9, 9]}, "expected": "Blue"}
        ],
        "hidden_test_cases": [
            {"id": 3, "input": {"k": 2, "train_data": [[[1, 1], "Cat"], [[2, 2], "Dog"], [[10, 10], "Bird"]], "target_point": [1.1, 1.1]}, "expected": "Cat"}
        ]
    },

    # =========================================================================
    # 7. DEVOPS
    # =========================================================================
    {
        "id": "devops-parse-logs",
        "title": "Parse Deployment Logs for Failures",
        "domain": "DevOps",
        "difficulty": "Easy",
        "tags": ["Log Parsing", "Regex", "DevOps"],
        "time_complexity": "O(n)",
        "space_complexity": "O(n)",
        "function_name": "count_failed_deployments",
        "comparator": "exact",
        "description": "Given a multi-line log string <code>logs</code> where lines containing <code>status=failed</code> or <code>error=</code> indicate failure, count and return the total number of distinct failed deployment lines.",
        "examples": [
            {"input": 'logs = "deploy-1 status=success\\ndeploy-2 status=failed error=oom\\ndeploy-3 status=success"', "output": "1"}
        ],
        "constraints": ["0 <= len(logs) <= 10^5"],
        "starter_code": "def count_failed_deployments(logs):\n    # Write your solution here\n    pass\n",
        "test_cases": [
            {"id": 1, "input": {"logs": "deploy-1 status=success\ndeploy-2 status=failed error=oom\ndeploy-3 status=success"}, "expected": 1},
            {"id": 2, "input": {"logs": "deploy-1 status=success"}, "expected": 0}
        ],
        "hidden_test_cases": [
            {"id": 3, "input": {"logs": "d1 error=timeout\nd2 status=failed\nd3 ok"}, "expected": 2}
        ]
    },
    {
        "id": "devops-retry-manager",
        "title": "Exponential Backoff Calculator",
        "domain": "DevOps",
        "difficulty": "Medium",
        "tags": ["Algorithms", "Resilience", "Networking"],
        "time_complexity": "O(attempts)",
        "space_complexity": "O(attempts)",
        "function_name": "calculate_backoff_delays",
        "comparator": "exact",
        "description": "Given <code>max_attempts</code>, <code>base_delay</code>, <code>factor</code>, and <code>max_delay</code>, calculate the list of delay intervals in seconds for each retry attempt: <code>min(base_delay * (factor ** (attempt - 1)), max_delay)</code> for attempt numbers 1 through max_attempts.",
        "examples": [
            {"input": "max_attempts = 4, base_delay = 1, factor = 2, max_delay = 5", "output": "[1, 2, 4, 5]"}
        ],
        "constraints": ["1 <= max_attempts <= 20", "base_delay >= 0"],
        "starter_code": "def calculate_backoff_delays(max_attempts, base_delay, factor, max_delay):\n    # Write your solution here\n    pass\n",
        "test_cases": [
            {"id": 1, "input": {"max_attempts": 4, "base_delay": 1, "factor": 2, "max_delay": 5}, "expected": [1, 2, 4, 5]},
            {"id": 2, "input": {"max_attempts": 2, "base_delay": 3, "factor": 2, "max_delay": 10}, "expected": [3, 6]}
        ],
        "hidden_test_cases": [
            {"id": 3, "input": {"max_attempts": 1, "base_delay": 10, "factor": 2, "max_delay": 20}, "expected": [10]}
        ]
    },
    {
        "id": "devops-dependency-resolver",
        "title": "Service Startup Dependency Resolver",
        "domain": "DevOps",
        "difficulty": "Hard",
        "tags": ["Graph", "Topological Sort", "DevOps"],
        "time_complexity": "O(V + E)",
        "space_complexity": "O(V + E)",
        "function_name": "service_startup_order",
        "comparator": "exact",
        "description": "Given a dictionary <code>service_dependencies</code> mapping each service to a list of services it directly depends on, return a valid startup sequence as a list of service names. If a circular dependency exists, return <code>None</code>.",
        "examples": [
            {"input": 'service_dependencies = {"db": [], "api": ["db"], "frontend": ["api"]}', "output": '["db", "api", "frontend"]'}
        ],
        "constraints": ["All service names are alphanumeric strings."],
        "starter_code": "def service_startup_order(service_dependencies):\n    # Write your solution here\n    pass\n",
        "test_cases": [
            {"id": 1, "input": {"service_dependencies": {"db": [], "api": ["db"], "frontend": ["api"]}}, "expected": ["db", "api", "frontend"]},
            {"id": 2, "input": {"service_dependencies": {"a": ["b"], "b": ["a"]}}, "expected": None}
        ],
        "hidden_test_cases": [
            {"id": 3, "input": {"service_dependencies": {"redis": []}}, "expected": ["redis"]}
        ]
    },

    # =========================================================================
    # 8. DATA ENGINEERING
    # =========================================================================
    {
        "id": "de-csv-aggregator",
        "title": "Aggregate Transaction Volumes",
        "domain": "Data Engineering",
        "difficulty": "Easy",
        "tags": ["Aggregation", "Hash Table", "ETL"],
        "time_complexity": "O(n)",
        "space_complexity": "O(k)",
        "function_name": "aggregate_transactions",
        "comparator": "exact",
        "description": "Given a list of transaction records <code>transactions</code> where each record is a dictionary <code>{'user_id': int, 'amount': float}</code>, compute and return a dictionary mapping each <code>user_id</code> to their total transaction sum rounded to 2 decimal places.",
        "examples": [
            {"input": "transactions = [{'user_id': 1, 'amount': 25.5}, {'user_id': 2, 'amount': 10.0}, {'user_id': 1, 'amount': 5.5}]", "output": "{1: 31.0, 2: 10.0}"}
        ],
        "constraints": ["0 <= len(transactions) <= 10^5"],
        "starter_code": "def aggregate_transactions(transactions):\n    # Write your solution here\n    pass\n",
        "test_cases": [
            {"id": 1, "input": {"transactions": [{"user_id": 1, "amount": 25.5}, {"user_id": 2, "amount": 10.0}, {"user_id": 1, "amount": 5.5}]}, "expected": {1: 31.0, 2: 10.0}},
            {"id": 2, "input": {"transactions": []}, "expected": {}}
        ],
        "hidden_test_cases": [
            {"id": 3, "input": {"transactions": [{"user_id": 99, "amount": 100.25}]}, "expected": {99: 100.25}}
        ]
    },
    {
        "id": "de-streaming-window",
        "title": "Tumpling Window Event Aggregator",
        "domain": "Data Engineering",
        "difficulty": "Medium",
        "tags": ["Stream Processing", "Time Series"],
        "time_complexity": "O(n)",
        "space_complexity": "O(w)",
        "function_name": "tumble_window_counts",
        "comparator": "exact",
        "description": "Given a list of integer event timestamps <code>events</code> and a window size in seconds <code>window_size</code>, group events into fixed tumbling windows starting at timestamp 0: window <code>[0, window_size)</code>, <code>[window_size, 2*window_size)</code>, etc. Return a dictionary mapping window index (0, 1, 2, ...) to event count.",
        "examples": [
            {"input": "events = [2, 5, 8, 12, 14], window_size = 5", "output": "{0: 1, 1: 2, 2: 2}"}
        ],
        "constraints": ["events are non-negative integers."],
        "starter_code": "def tumble_window_counts(events, window_size):\n    # Write your solution here\n    pass\n",
        "test_cases": [
            {"id": 1, "input": {"events": [2, 5, 8, 12, 14], "window_size": 5}, "expected": {0: 1, 1: 2, 2: 2}},
            {"id": 2, "input": {"events": [0, 1, 2], "window_size": 10}, "expected": {0: 3}}
        ],
        "hidden_test_cases": [
            {"id": 3, "input": {"events": [], "window_size": 5}, "expected": {}}
        ]
    },
    {
        "id": "de-join-datasets",
        "title": "Hash Join Implementation",
        "domain": "Data Engineering",
        "difficulty": "Hard",
        "tags": ["Databases", "Hash Join", "Algorithms"],
        "time_complexity": "O(R + S)",
        "space_complexity": "O(R)",
        "function_name": "inner_hash_join",
        "comparator": "unordered_list",
        "description": "Implement an inner hash join between two datasets <code>left_table</code> and <code>right_table</code> on key <code>join_key</code>. Each table is a list of dictionaries. Return a list of merged dictionaries containing all keys from both matched records.",
        "examples": [
            {"input": "left_table = [{'id': 1, 'name': 'A'}], right_table = [{'id': 1, 'role': 'Admin'}], join_key = 'id'", "output": "[{'id': 1, 'name': 'A', 'role': 'Admin'}]"}
        ],
        "constraints": ["1 <= len(left_table), len(right_table) <= 10^4"],
        "starter_code": "def inner_hash_join(left_table, right_table, join_key):\n    # Write your solution here\n    pass\n",
        "test_cases": [
            {"id": 1, "input": {"left_table": [{"id": 1, "name": "A"}], "right_table": [{"id": 1, "role": "Admin"}], "join_key": "id"}, "expected": [{"id": 1, "name": "A", "role": "Admin"}]},
            {"id": 2, "input": {"left_table": [{"id": 2, "v": 10}], "right_table": [{"id": 3, "v": 20}], "join_key": "id"}, "expected": []}
        ],
        "hidden_test_cases": [
            {"id": 3, "input": {"left_table": [{"k": 1, "a": 1}, {"k": 2, "a": 2}], "right_table": [{"k": 2, "b": 20}], "join_key": "k"}, "expected": [{"k": 2, "a": 2, "b": 20}]}
        ]
    },

    # =========================================================================
    # 9. CYBERSECURITY
    # =========================================================================
    {
        "id": "sec-password-strength",
        "title": "Password Strength Validator",
        "domain": "Cybersecurity",
        "difficulty": "Easy",
        "tags": ["Security", "Regex", "Validation"],
        "time_complexity": "O(n)",
        "space_complexity": "O(1)",
        "function_name": "is_strong_password",
        "comparator": "exact",
        "description": "A strong password must meet all of the following criteria:<br>1. At least 8 characters long.<br>2. Contains at least one uppercase letter.<br>3. Contains at least one lowercase letter.<br>4. Contains at least one digit.<br>5. Contains at least one special character from <code>!@#$%^&*()-_=+</code>.<br><br>Return <code>true</code> if strong, <code>false</code> otherwise.",
        "examples": [
            {"input": 'password = "Secur3P@ssword"', "output": "true"},
            {"input": 'password = "weak"', "output": "false"}
        ],
        "constraints": ["1 <= len(password) <= 100"],
        "starter_code": "def is_strong_password(password):\n    # Write your solution here\n    pass\n",
        "test_cases": [
            {"id": 1, "input": {"password": "Secur3P@ssword"}, "expected": True},
            {"id": 2, "input": {"password": "weak"}, "expected": False}
        ],
        "hidden_test_cases": [
            {"id": 3, "input": {"password": "AllLettersNoDigits!"}, "expected": False},
            {"id": 4, "input": {"password": "P@ss1"}, "expected": False}
        ]
    },
    {
        "id": "sec-brute-force-detector",
        "title": "Brute Force Login Detector",
        "domain": "Cybersecurity",
        "difficulty": "Medium",
        "tags": ["Security", "Sliding Window", "Anomaly Detection"],
        "time_complexity": "O(n)",
        "space_complexity": "O(k)",
        "function_name": "detect_brute_force_ips",
        "comparator": "unordered_list",
        "description": "Given a list of login attempts <code>logs</code> where each entry is <code>{'ip': str, 'status': 'success'|'failed', 'timestamp': int}</code>, return a list of unique IP addresses that generated <code>threshold</code> or more failed login attempts within any <code>window_seconds</code> interval.",
        "examples": [
            {"input": "logs = [{'ip': '1.1.1.1', 'status': 'failed', 'timestamp': 10}, {'ip': '1.1.1.1', 'status': 'failed', 'timestamp': 20}], threshold = 2, window_seconds = 60", "output": "['1.1.1.1']"}
        ],
        "constraints": ["1 <= len(logs) <= 10^4", "threshold >= 1", "window_seconds >= 1"],
        "starter_code": "def detect_brute_force_ips(logs, threshold, window_seconds):\n    # Write your solution here\n    pass\n",
        "test_cases": [
            {"id": 1, "input": {"logs": [{"ip": "1.1.1.1", "status": "failed", "timestamp": 10}, {"ip": "1.1.1.1", "status": "failed", "timestamp": 20}], "threshold": 2, "window_seconds": 60}, "expected": ["1.1.1.1"]},
            {"id": 2, "input": {"logs": [{"ip": "2.2.2.2", "status": "success", "timestamp": 10}], "threshold": 2, "window_seconds": 60}, "expected": []}
        ],
        "hidden_test_cases": [
            {"id": 3, "input": {"logs": [{"ip": "3.3.3.3", "status": "failed", "timestamp": 10}, {"ip": "3.3.3.3", "status": "failed", "timestamp": 100}], "threshold": 2, "window_seconds": 30}, "expected": []}
        ]
    },
    {
        "id": "sec-intrusion-pattern",
        "title": "Security Event Sliding Window Correlator",
        "domain": "Cybersecurity",
        "difficulty": "Hard",
        "tags": ["Security", "Pattern Matching", "State Machine"],
        "time_complexity": "O(n)",
        "space_complexity": "O(n)",
        "function_name": "correlate_attack_pattern",
        "comparator": "exact",
        "description": "Given a chronological stream of event tags <code>events</code> and an attack signature sequence <code>signature</code> (e.g. <code>['scan', 'exploit', 'exfil']</code>), return the count of non-overlapping occurrences of the signature subsequence within the stream.",
        "examples": [
            {"input": "events = ['scan', 'ping', 'exploit', 'exfil', 'scan', 'exploit', 'exfil'], signature = ['scan', 'exploit', 'exfil']", "output": "2"}
        ],
        "constraints": ["1 <= len(events) <= 10^5", "1 <= len(signature) <= 10"],
        "starter_code": "def correlate_attack_pattern(events, signature):\n    # Write your solution here\n    pass\n",
        "test_cases": [
            {"id": 1, "input": {"events": ["scan", "ping", "exploit", "exfil", "scan", "exploit", "exfil"], "signature": ["scan", "exploit", "exfil"]}, "expected": 2},
            {"id": 2, "input": {"events": ["scan", "exploit"], "signature": ["scan", "exploit", "exfil"]}, "expected": 0}
        ],
        "hidden_test_cases": [
            {"id": 3, "input": {"events": ["a", "b", "c"], "signature": ["a", "b", "c"]}, "expected": 1}
        ]
    },

    # =========================================================================
    # 10. MOBILE DEVELOPMENT
    # =========================================================================
    {
        "id": "mob-format-phone-number",
        "title": "Validate & Normalize Phone Number",
        "domain": "Mobile Development",
        "difficulty": "Easy",
        "tags": ["Mobile", "String", "Validation"],
        "time_complexity": "O(n)",
        "space_complexity": "O(n)",
        "function_name": "normalize_phone_number",
        "comparator": "exact",
        "description": "Given a phone number string <code>phone</code> containing digits and formatting symbols (spaces, dashes, parentheses), strip all non-digit characters. If the resulting string has exactly 10 digits, format it as <code>(XXX) XXX-XXXX</code>. If invalid, return <code>None</code>.",
        "examples": [
            {"input": 'phone = "123-456-7890"', "output": '"(123) 456-7890"'},
            {"input": 'phone = "12345"', "output": "null"}
        ],
        "constraints": ["0 <= len(phone) <= 30"],
        "starter_code": "def normalize_phone_number(phone):\n    # Write your solution here\n    pass\n",
        "test_cases": [
            {"id": 1, "input": {"phone": "123-456-7890"}, "expected": "(123) 456-7890"},
            {"id": 2, "input": {"phone": "12345"}, "expected": None}
        ],
        "hidden_test_cases": [
            {"id": 3, "input": {"phone": "(555) 019-2834"}, "expected": "(555) 019-2834"},
            {"id": 4, "input": {"phone": "+1 555 123 4567"}, "expected": None}
        ]
    },
    {
        "id": "mob-offline-sync-queue",
        "title": "Mobile Offline Sync Queue",
        "domain": "Mobile Development",
        "difficulty": "Medium",
        "tags": ["Mobile", "Offline Sync", "Queue"],
        "time_complexity": "O(n)",
        "space_complexity": "O(n)",
        "function_name": "compact_sync_queue",
        "comparator": "exact",
        "description": "In an offline-first mobile app, actions on entities are queued as <code>{'entity_id': int, 'action': 'create'|'update'|'delete', 'data': dict}</code>.<br><br>Implement <code>compact_sync_queue(queue)</code> to compact redundant operations for each <code>entity_id</code>:<br>- If an entity is created then deleted before syncing, eliminate both operations completely.<br>- If created then updated, keep a single 'create' with merged data.<br>- Multiple updates should be collapsed into a single latest merged update.<br>Return the list of compacted actions.",
        "examples": [
            {"input": "queue = [{'entity_id': 1, 'action': 'create', 'data': {'name': 'A'}}, {'entity_id': 1, 'action': 'delete', 'data': {}}]", "output": "[]"}
        ],
        "constraints": ["0 <= len(queue) <= 1000"],
        "starter_code": "def compact_sync_queue(queue):\n    # Write your solution here\n    pass\n",
        "test_cases": [
            {"id": 1, "input": {"queue": [{"entity_id": 1, "action": "create", "data": {"name": "A"}}, {"entity_id": 1, "action": "delete", "data": {}}]}, "expected": []},
            {"id": 2, "input": {"queue": [{"entity_id": 2, "action": "create", "data": {"title": "X"}}, {"entity_id": 2, "action": "update", "data": {"price": 10}}]}, "expected": [{"entity_id": 2, "action": "create", "data": {"title": "X", "price": 10}}]}
        ],
        "hidden_test_cases": [
            {"id": 3, "input": {"queue": [{"entity_id": 3, "action": "update", "data": {"a": 1}}, {"entity_id": 3, "action": "update", "data": {"b": 2}}]}, "expected": [{"entity_id": 3, "action": "update", "data": {"a": 1, "b": 2}}]}
        ]
    },
    {
        "id": "mob-resource-throttler",
        "title": "Mobile Battery & Network Request Prioritizer",
        "domain": "Mobile Development",
        "difficulty": "Hard",
        "tags": ["Optimization", "Greedy", "Mobile"],
        "time_complexity": "O(n log n)",
        "space_complexity": "O(n)",
        "function_name": "prioritize_mobile_requests",
        "comparator": "exact",
        "description": "Given a battery percentage <code>battery_level</code> (0-100), network type <code>network</code> ('wifi' or 'cellular'), and a list of pending requests with <code>id</code>, <code>size_kb</code>, and <code>importance</code> ('critical', 'normal', 'background'):<br>- On low battery (< 20%) or cellular network, drop 'background' requests.<br>- Order remaining requests by importance ('critical' first, then 'normal') then by smallest <code>size_kb</code>.<br>Return the ordered list of request <code>id</code>s.",
        "examples": [
            {"input": "battery_level = 15, network = 'cellular', requests = [{'id': '1', 'size_kb': 500, 'importance': 'background'}, {'id': '2', 'size_kb': 200, 'importance': 'normal'}, {'id': '3', 'size_kb': 100, 'importance': 'critical'}]", "output": "['3', '2']"}
        ],
        "constraints": ["1 <= len(requests) <= 1000"],
        "starter_code": "def prioritize_mobile_requests(battery_level, network, requests):\n    # Write your solution here\n    pass\n",
        "test_cases": [
            {"id": 1, "input": {"battery_level": 15, "network": "cellular", "requests": [{"id": "1", "size_kb": 500, "importance": "background"}, {"id": "2", "size_kb": 200, "importance": "normal"}, {"id": "3", "size_kb": 100, "importance": "critical"}]}, "expected": ["3", "2"]},
            {"id": 2, "input": {"battery_level": 80, "network": "wifi", "requests": [{"id": "A", "size_kb": 50, "importance": "background"}, {"id": "B", "size_kb": 100, "importance": "critical"}]}, "expected": ["B", "A"]}
        ],
        "hidden_test_cases": [
            {"id": 3, "input": {"battery_level": 10, "network": "wifi", "requests": [{"id": "X", "size_kb": 10, "importance": "background"}]}, "expected": []}
        ]
    }
]

# Quick lookup by ID
QUESTION_MAP: Dict[str, Dict[str, Any]] = {q["id"]: q for q in QUESTION_BANK}


def normalize_domain_name(domain: Optional[str]) -> str:
    """Matches any arbitrary user domain string to one of the 10 supported domains."""
    if not domain:
        return "Software Engineering"

    d = domain.lower()
    if "back" in d or "api" in d or "node" in d or "flask" in d or "django" in d or "server" in d:
        return "Backend Development"
    if "front" in d or "react" in d or "angular" in d or "vue" in d or "ui" in d or "web" in d:
        return "Frontend Development"
    if "full" in d or "stack" in d or "mern" in d:
        return "Full Stack Development"
    if "data sci" in d or "analytics" in d or "statistic" in d or "analyst" in d:
        return "Data Science"
    if "ai" in d or "machine" in d or "ml" in d or "deep" in d or "vision" in d or "nlp" in d:
        return "AI / Machine Learning"
    if "devops" in d or "cloud" in d or "sre" in d or "infra" in d or "kubernetes" in d or "docker" in d:
        return "DevOps"
    if "data eng" in d or "etl" in d or "pipeline" in d or "spark" in d:
        return "Data Engineering"
    if "mobile" in d or "android" in d or "ios" in d or "flutter" in d or "react native" in d:
        return "Mobile Development"
    if "cyber" in d or "sec" in d or "pentest" in d or "infosec" in d:
        return "Cybersecurity"

    return "Software Engineering"


def get_questions_for_assessment(
    domain: Optional[str] = "Software Engineering",
    difficulty: Optional[str] = "Medium",
    count: int = 5,
    role: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Selects a dynamically tailored set of non-duplicate questions based on:
    - Domain (10 domains)
    - Difficulty (Easy, Medium, Hard distribution)
    - Count (3, 5, 8)
    
    Difficulty distributions:
    - Easy: 60% Easy, 40% Medium
    - Medium: 30% Easy, 50% Medium, 20% Hard
    - Hard: 20% Medium, 50% Hard, 30% Very Hard / Hard
    """
    matched_domain = normalize_domain_name(domain)
    diff = (difficulty or "Medium").capitalize()
    if diff not in ["Easy", "Medium", "Hard"]:
        diff = "Medium"

    count = int(count) if count in [3, 5, 8] else 5

    # Filter pool by primary domain; if pool has fewer than count, supplement from Software Engineering
    primary_pool = [q for q in QUESTION_BANK if q["domain"] == matched_domain]
    fallback_pool = [q for q in QUESTION_BANK if q["domain"] == "Software Engineering" and q not in primary_pool]
    general_pool = [q for q in QUESTION_BANK if q not in primary_pool and q not in fallback_pool]

    all_available = primary_pool + fallback_pool + general_pool

    # Partition by difficulty
    easy_qs = [q for q in all_available if q["difficulty"] == "Easy"]
    med_qs = [q for q in all_available if q["difficulty"] == "Medium"]
    hard_qs = [q for q in all_available if q["difficulty"] == "Hard"]

    # Determine distribution counts
    if count == 3:
        if diff == "Easy":
            req_easy, req_med, req_hard = 2, 1, 0
        elif diff == "Hard":
            req_easy, req_med, req_hard = 0, 1, 2
        else: # Medium
            req_easy, req_med, req_hard = 1, 1, 1
    elif count == 8:
        if diff == "Easy":
            req_easy, req_med, req_hard = 5, 3, 0
        elif diff == "Hard":
            req_easy, req_med, req_hard = 1, 4, 3
        else: # Medium
            req_easy, req_med, req_hard = 2, 4, 2
    else: # Default 5 questions
        if diff == "Easy":
            req_easy, req_med, req_hard = 3, 2, 0
        elif diff == "Hard":
            req_easy, req_med, req_hard = 1, 2, 2
        else: # Medium: 30% Easy (1-2), 50% Med (2-3), 20% Hard (1)
            req_easy, req_med, req_hard = 1, 3, 1

    selected: List[Dict[str, Any]] = []
    selected_ids = set()

    def pick_from(candidates: List[Dict[str, Any]], needed: int):
        nonlocal selected, selected_ids
        for c in candidates:
            if needed <= 0:
                break
            if c["id"] not in selected_ids:
                selected.append(copy.deepcopy(c))
                selected_ids.add(c["id"])
                needed -= 1

    pick_from(easy_qs, req_easy)
    pick_from(med_qs, req_med)
    pick_from(hard_qs, req_hard)

    # If count not met, fill with any remaining questions
    if len(selected) < count:
        pick_from(all_available, count - len(selected))

    # Sort selected by difficulty progression: Easy -> Medium -> Hard
    diff_order = {"Easy": 1, "Medium": 2, "Hard": 3}
    selected.sort(key=lambda q: diff_order.get(q["difficulty"], 2))

    # Assign 1-indexed numbering for UI
    for idx, q in enumerate(selected, 1):
        q["index"] = idx
        q["numberText"] = f"Problem {idx} of {len(selected)}"
        q["progressText"] = f"Question {idx} of {len(selected)}"
        q["progressPercent"] = round((idx / len(selected)) * 100)

    return selected


def get_question_by_key(key: str) -> Optional[Dict[str, Any]]:
    """Retrieve a question by ID or title key from the question bank."""
    key_clean = key.lower().strip()
    for q in QUESTION_BANK:
        if q["id"].lower() == key_clean or q["id"].lower().endswith(key_clean) or key_clean in q["id"].lower():
            return copy.deepcopy(q)
        if q["title"].lower().replace(" ", "-") == key_clean.replace(" ", "-"):
            return copy.deepcopy(q)
    return None


def score_question(
    code: str,
    run_result: Dict[str, Any],
    time_limit_ms: float = 200.0
) -> Dict[str, Any]:
    """
    Deterministic scoring engine based on:
    - Test cases: 60%
    - Algorithm efficiency: 20%
    - Code correctness: 10%
    - Code quality: 10%
    Total: 100 points per question.
    """
    passed = run_result.get("passed", 0)
    total = run_result.get("total", 0) or 1
    status = run_result.get("status", "Failed")
    exec_time = float(run_result.get("execution_time_ms", 0) or 0)

    # Check for infrastructure error
    if run_result.get("is_infrastructure_error") or status == "Execution Unavailable":
        return {
            "score": 0.0,
            "test_case_score": 0.0,
            "efficiency_score": 0.0,
            "correctness_score": 0.0,
            "quality_score": 0.0,
            "status": "Execution Unavailable",
            "pass_ratio": 0.0,
            "execution_time_ms": 0.0,
            "is_infrastructure_error": True
        }

    # 1. Test Cases (60 pts)
    pass_ratio = passed / total
    test_case_score = round(pass_ratio * 60.0, 1)

    # 2. Algorithm Efficiency (20 pts)
    efficiency_score = 0.0
    if status == "Passed":
        if exec_time <= 50.0:
            efficiency_score = 20.0
        elif exec_time <= time_limit_ms:
            efficiency_score = 16.0
        else:
            efficiency_score = 10.0
    elif pass_ratio > 0 and status != "Timeout":
        efficiency_score = round(pass_ratio * 10.0, 1)

    # 3. Code Correctness (10 pts)
    correctness_score = 0.0
    if status == "Passed":
        correctness_score = 10.0
    elif pass_ratio >= 0.5:
        correctness_score = 5.0

    # 4. Code Quality (10 pts)
    quality_score = 0.0
    stripped_code = code.strip() if code else ""
    if pass_ratio > 0 or status == "Passed":
        if len(stripped_code) > 20:
            quality_score += 3.0
        if "def " in stripped_code and "return " in stripped_code:
            quality_score += 3.0
        if any(kw in stripped_code for kw in ["for ", "while ", "if ", "dict(", "{", "["]):
            quality_score += 2.0
        if any(line.strip().startswith("#") for line in stripped_code.splitlines()) or '"""' in stripped_code or "'''" in stripped_code:
            quality_score += 2.0

    quality_score = min(10.0, quality_score)

    total_question_score = round(test_case_score + efficiency_score + correctness_score + quality_score, 1)

    # Status classification
    if pass_ratio == 1.0:
        q_status = "Solved"
    elif pass_ratio > 0:
        q_status = "Partially Solved"
    elif status in ["Syntax Error", "Timeout", "Runtime Error"]:
        q_status = status
    else:
        q_status = "Not Solved"

    return {
        "score": total_question_score,
        "test_case_score": test_case_score,
        "efficiency_score": efficiency_score,
        "correctness_score": correctness_score,
        "quality_score": quality_score,
        "status": q_status,
        "pass_ratio": pass_ratio,
        "execution_time_ms": exec_time,
        "is_infrastructure_error": False
    }
