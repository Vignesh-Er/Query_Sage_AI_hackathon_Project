SELECT * FROM rental WHERE YEAR(rental_date) = 2005 AND customer_id IN (SELECT customer_id FROM customer WHERE LOWER(email) LIKE '%@gmail.com');
