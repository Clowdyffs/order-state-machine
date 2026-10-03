# What I built:

I built an order state machine in python, testing with pytest, api implemented via fastapi.

I used python because personally I think it's the most readable, and easiest to iterate on. I used fastAPI simply because I am the most familiar with it, even though it does have tradeoffs that i'll explain.

## how to run it:

Use Python 3.10 or newer. From the repo directory:

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Start the API:

```sh
python -m uvicorn api:app --reload
```

Open http://127.0.0.1:8000/docs to try the endpoints:

- `POST /orders` creates an order and returns its ID.
- `POST /orders/{order_id}/advance` advances it one step. Call twice for the happy path.
- `GET /orders/{order_id}` returns the current state and timestamped history.

Run the tests:

```sh
python -m pytest -q
```

Run with one worker. Orders are stored in memory, so restarting or reloading the server clears them. The running API uses successful payment and completion stubs; tests mock the failure cases.

## tradeoffs:

First off, the language is a tradeoff if this were to be a production system. If i had to choose a language for a production system, I would most likely choose rust, with go as the runner up.

Second, the way fastAPI was implemented uses a global lock, which isn't scalable at all since it serializes everything. A more ideal api setup would have better parallelization, since I just have one global lock for simplicity, which serializes all operations across all orders (bad scaling).

I'm going to treat this question as more of a "if you had to build a more production ready system", since time wasn't a big issue for me. I would start on the api side, and implementing a more scalable version that coordinates better. I'd also obviously use a different language since python was picked mostly for illustration. I would also test how it handles large bursts of orders, since the inherent behavior is "last-minute" so there could potentially be lots of orders in a short period of time, with also the amount of tickets running out during the burst.

## ai usage:

For my ai tools, I used GPT 6.1 sol (high) on the codex harness via t3-code. I picked this since I didn't really need a super powerful model or a higher thinking effort, so it's cheap while also being reliable for the task I was doing. t3-code is just my interface of choice.

Ai was used to proofread code, and also implement my pre-defined architecture decisions (more for speed rather than implementation quality, I proofread and corrected mistakes or unnecessary code), and implement the `payment.py` stub payment system. didn't really need a more complex setup for this task, I can explain every line of code with ease.

docs were fully handwritten except for the above section on how to run it.

### How I validated or challenged outputs, specifically:

I read all the code implemented throughout the entire process, and I also was fully responsible for picking language, architecture, and organization. One example from the process was as early as implementing the "order" data structure, where it decided not to implement the `set_state` function. Which is arguably the most important pre-requisite for implementing the state machine, since that's what handles and records state-changes and timestamps.

---

This following section is my recorded thoughts throughout the entire implementation process.

For reference, this README will be written in a linear order to easily track my thoughts through the building process. Things will be recorded in roughly the order I think/do them.

## Pre-code brainstorm:

Before even getting into code or implementation, my instinct is to just go with python. Simplest, easiest to read, quickest to iterate on, and portable. Also can use fastapi for the api since i'm already familiar with it and it makes my docs for me. just need to make sure to use locks in the right place since it uses a thread pool.

as for my process, most likely going to use test driven development, its the most obvious approach since tests are a requirement anyways. probably just going to write the tests and fulfill them one at a time from easiest case to hardest.

as for the stub payment, ai will be a big help since in a real scenario, you wouldn't typically implement that yourself, it would be offloaded to a separate company, such as stripe.

best starting point is writing the tests + stub payment, and then state machine and api is essentially the remaining work.

as for how the state machine will work, it will essentially be checking if payment is authorized, if yes then attempt to complete order (otherwise can easily reject), if that fails then attempt to void the payment and mark order as cancelled (after/if void is confirmed). if that somehow fails, probably in the real world it would happen due to payment processor issues so I can recreate that through the stub, so would need to move to needs_attention without relying on any outside systems to propagate that.

timestamps will be recorded every time the state changes on an order (for example initialized -> payment authorized will record a timestamp when authorization is confirmed)

---

The rough idea of the stub payment system before i write the tests is have a simple `authorize(order_id)` and `void(order_id)` method, should be able to just raise an exception if the authorization or void fails. can mock failures in the test by raising the exceptions for either case. and simply return a success code like 200 if it was a success.

also need a simple datastructure for orders, pretty much just going to be exceptions, the order id, current state, and a tuple array to track state changes. when an order is created it, the tuple should be something like `[("initialized", timestamp)]`

---

alright, tests implemented with the rough shape of things. time for the payment system and data structure since we need those to start implementing the state machine.

also added a function to the order data structure to handle updating the state (appending to the tuple array with the new state and the timestamp).

---

all tests fail, demonstrated by `python -m pytest -q`

now to implement the easy case where everything goes well. not doing any checks yet since we are assuming just the init -> authorize -> complete.

passes the `test_happy_path` test now

---

now for the next case, a rejected payment. just have to add a check to see if we get a success code or the `PaymentDeclined` exception, we can set the status to rejected if we get that exception.

happy path + payment rejection tests now pass

---

next is the `CompletionFailed` exception after we see the payment was authorized. we have to call void with the order id, for this test we don't have to check if the void fails yet, just assume it voids and cancel the order.

now the `test_completion_failure_with_successful_void` test passes too.

---

last case, now we just need to an a check onto the previous case to check if we got a success code or the `VoidFailed` exception. then escalate it if we do get the exception.

all tests pass now, advancing from an invalid state would raise a `ValueError` exception.

---

now to implement the api, gonna still use fastapi

implemented via fastapi, gpt 6.1 sol also added some boilerplate tests for it (more info on ai stuffs toward at the top)
