import os
import csv
import time
import board
import adafruit_dht
import pigpio
from threading import Thread
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

CSV_FILENAME = 'schedules.csv'

# Global variables
min_temp = 18
max_temp = 22
celsius = False

# Initialize pigpio
pi = pigpio.pi()

@app.route('/')
def index():
    return render_template('index.html', title='ThermoPi')


def write_schedule_to_csv(schedule_id, start_time, min_temp, max_temp):
    """Append a new schedule to the CSV file."""
    try:
        with open(CSV_FILENAME, mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([schedule_id, start_time, min_temp, max_temp])
    except Exception as e:
        print(f"Error writing to CSV: {e}")


def remove_schedule_from_csv(schedule_id):
    """Remove a schedule from the CSV file by ID."""
    temp_filename = 'temp_schedules.csv'
    try:
        with open(CSV_FILENAME, mode='r', newline='') as file, open(temp_filename, mode='w', newline='') as temp_file:
            reader = csv.reader(file)
            writer = csv.writer(temp_file)
            schedule_found = False
            for row in reader:
                if row[0] != schedule_id:
                    writer.writerow(row)
                else:
                    schedule_found = True
        if schedule_found:
            os.remove(CSV_FILENAME)
            os.rename(temp_filename, CSV_FILENAME)
        else:
            os.remove(temp_filename)
    except Exception as e:
        print(f"Error removing schedule from CSV: {e}")


def toggle_heat():
    try:
        if pi.read(heat_pin) == pigpio.LOW:
            # Start Heat and fan
            pi.write(heat_pin, pigpio.HIGH)
            pi.write(fan_pin, pigpio.HIGH)
        else:
            # Stop Heat and fan
            pi.write(heat_pin, pigpio.LOW)
            pi.write(fan_pin, pigpio.LOW)
        return True
    except Exception as e:
        pi.write(heat_pin, pigpio.LOW)
        pi.write(fan_pin, pigpio.LOW)
        print(f"Error toggling heat: {e}")
        return False


def toggle_cool():
    try:
        if pi.read(cool_pin) == pigpio.LOW:
            # Start cool and fan
            pi.write(cool_pin, pigpio.HIGH)
            pi.write(fan_pin, pigpio.HIGH)
        else:
            # Stop cool and fan
            pi.write(cool_pin, pigpio.LOW)
            pi.write(fan_pin, pigpio.LOW)
        return True
    except Exception as e:
        pi.write(cool_pin, pigpio.LOW)
        pi.write(fan_pin, pigpio.LOW)
        print(f"Error toggling cool: {e}")
        return False


def maintain_temp():
    while True:
        try:
            if min_temp <= thermo.temperature <= max_temp and (pi.read(heat_pin) != pigpio.LOW or pi.read(cool_pin) != pigpio.LOW):
                pi.write(heat_pin, pigpio.LOW)
                pi.write(cool_pin, pigpio.LOW)
                pi.write(fan_pin, pigpio.LOW)
            else:
                if min_temp >= thermo.temperature and pi.read(heat_pin) == pigpio.LOW:
                    toggle_heat()
                if max_temp <= thermo.temperature and pi.read(cool_pin) == pigpio.LOW:
                    toggle_cool()
            time.sleep(60)  # Sleep for 60 seconds before checking again
        except Exception as e:
            print(f"Error in maintain_temp: {e}")


@app.route('/toggle_fan/', methods=['POST'])
def toggle_fan():
    try:
        if pi.read(fan_pin) == pigpio.LOW:
            pi.write(fan_pin, pigpio.HIGH)
        else:
            pi.write(fan_pin, pigpio.LOW)
        return jsonify({'message': 'Fan state toggled successfully'}), 200
    except Exception as e:
        print(f"Error toggling fan: {e}")
        return jsonify({'error': 'Unable to toggle fan'}), 500


@app.route('/set_temps/', methods=['POST'])
def set_temps():
    global min_temp, max_temp
    try:
        data = request.get_json()
        min_temp = data.get('min_temp', min_temp)
        max_temp = data.get('max_temp', max_temp)
        return jsonify({'message': 'Temperatures updated successfully'}), 200
    except Exception as e:
        print(f"Error setting temperatures: {e}")
        return jsonify({'error': 'Unable to set temperatures'}), 500


@app.route('/get_temp/', methods=['GET'])
def get_temp():
    try:
        temperature = thermo.temperature * (9 / 5) + 32 if not celsius else thermo.temperature
        humidity = thermo.humidity
        return jsonify({'temperature': temperature, 'humidity': humidity}), 200
    except Exception as e:
        print(f"Error getting temperature: {e}")
        return jsonify({'error': 'Unable to read temperature'}), 500


@app.route('/get_max/', methods=['GET'])
def get_max():
    try:
        max_temp_celsius = max_temp
        if not celsius:
            max_temp_celsius = max_temp * (9 / 5) + 32
        return jsonify({'max_temp': max_temp_celsius}), 200
    except Exception as e:
        print(f"Error getting max temperature: {e}")
        return jsonify({'error': 'Unable to read max temperature'}), 500


@app.route('/get_min/', methods=['GET'])
def get_min():
    try:
        min_temp_celsius = min_temp
        if not celsius:
            min_temp_celsius = min_temp * (9 / 5) + 32
        return jsonify({'min_temp': min_temp_celsius}), 200
    except Exception as e:
        print(f"Error getting min temperature: {e}")
        return jsonify({'error': 'Unable to read min temperature'}), 500


@app.route('/toggle_unit/', methods=['POST'])
def toggle_unit():
    global celsius
    celsius = not celsius
    return jsonify({'message': 'Unit toggled successfully', 'celsius': celsius}), 200


@app.route('/schedules', methods=['POST'])
def add_schedule():
    data = request.get_json()
    try:
        schedule_id = data['schedule_id']
        start_time = data['start_time']
        min_temp = data['min_temp']
        max_temp = data['max_temp']
        write_schedule_to_csv(schedule_id, start_time, min_temp, max_temp)
        return jsonify({'message': 'Schedule added successfully'}), 201
    except KeyError:
        return jsonify({'error': 'Missing required data'}), 400
    except Exception as e:
        print(f"Error adding schedule: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/schedules/<schedule_id>', methods=['DELETE'])
def delete_schedule(schedule_id):
    try:
        remove_schedule_from_csv(schedule_id)
        return jsonify({'message': 'Schedule removed successfully'}), 200
    except Exception as e:
        print(f"Error deleting schedule: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/schedules', methods=['GET'])
def get_schedules():
    try:
        with open(CSV_FILENAME, mode='r', newline='') as file:
            reader = csv.reader(file)
            schedules = [{'schedule_id': row[0], 'start_time': row[1], 'min_temp': row[2], 'max_temp': row[3]} for row in reader]
        return jsonify(schedules), 200
    except Exception as e:
        print(f"Error getting schedules: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    # Declare GPIO pins
    heat_pin = 37
    cool_pin = 35
    fan_pin = 33
    extra_pin = 31
    thermo = adafruit_dht.DHT22(board.D4)

    # Start toggle thread
    Thread(target=maintain_temp, daemon=True).start()

    app.run(debug=False, port=5757, host='0.0.0.0', ssl_context='adhoc')
