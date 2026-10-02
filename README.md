For reference, this README will be written in a linear order to easily track my thoughts through the building process. Things will be recorded in roughly the order I think/do them. 

Pre-code brainstorm: 

Before even getting into code or implementation, my instinct is to just go with python. Simplest, easiest to read, quickest to iterate on, and portable. Also can use fastapi for the api since i'm already familiar with it and it makes my docs for me. just need to make sure to use locks in the right place since it uses a thread pool. 

as for my process, most likely going to use test driven development, its the most obvious approach since tests are a requirement anyways. probably just going to write the tests and fulfill them one at a time from easiest case to hardest. 

as for the stub payment, ai will be a big help since in a real scenario, you wouldn't typically implement that yourself, it would be offloaded to a separate company, such as stripe. 

best starting point is writing the tests + stub payment, and then state machine and api is essentially the remaining work. 

as for how the state machine will work, it will essentially be checking if payment is authorized, if yes then attempt to complete order (otherwise can easily reject), if that fails then attempt to void the payment and mark order as cancelled (after/if void is confirmed). if that somehow fails, probably in the real world it would happen due to payment processor issues so I can recreate that through the stub, so would need to move to needs_attention without relying on any outside systems to propagate that. timestamps will be recorded every time the state changes on an order (for example initialized -> payment authorized will record a timestamp when authorization is confirmed)

-----

The rough idea of the stub payment system before i write the tests is have a simple authorize(order_id) and void(order_id) method, should be able to just raise an exception if the authorization or void fails. can mock failures in the test by raising the exceptions for either case. and simply return a success code like 200 if it was a success. 

also need a simple datastructure for orders, pretty much just going to be exceptions, the order id, current state, and a tuple array to track state changes. when an order is created it, the tuple should be something like [("initialized", timestamp)]

